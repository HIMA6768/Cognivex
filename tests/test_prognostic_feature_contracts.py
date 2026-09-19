from __future__ import annotations

from dataclasses import replace
import math

import pytest

from src.contracts.prognostic_features import (
    COEF_EPS,
    DIRECTION_DISPLAY_TEXT,
    FEATURE_EFFECTS_CSV_COLUMNS,
    EffectDirection,
    FeatureType,
    GenomicFeatureMapping,
    PenalizedCoxSummaryValues,
    PrognosticFeatureAnalysisResult,
    PrognosticFeatureEffect,
)


def _summary() -> PenalizedCoxSummaryValues:
    return PenalizedCoxSummaryValues(
        standard_error=0.1,
        beta_ci_lower_95=-0.2,
        beta_ci_upper_95=0.4,
        hazard_ratio_ci_lower_95=0.8,
        hazard_ratio_ci_upper_95=1.5,
        comparison_to=0.0,
        z_statistic=1.2,
        p_value=0.2,
        negative_log2_p_value=2.321928,
    )


def _effect(order: int, feature_type: FeatureType) -> PrognosticFeatureEffect:
    raw = f"gene_{order}" if feature_type is FeatureType.EXPRESSION else f"gene_{order}_mut"
    model = raw if feature_type is FeatureType.EXPRESSION else f"{raw}_present"
    beta = 0.1 + order / 1000
    return PrognosticFeatureEffect(
        rank=order,
        frozen_genomic_order=order,
        raw_feature_name=raw,
        model_feature_name=model,
        feature_type=feature_type,
        beta=beta,
        abs_beta=abs(beta),
        hazard_ratio=math.exp(beta),
        direction=EffectDirection.HIGHER,
        direction_display=DIRECTION_DISPLAY_TEXT[EffectDirection.HIGHER],
        is_active=True,
        model_summary=_summary(),
    )


def _complete_effects() -> tuple[PrognosticFeatureEffect, ...]:
    return tuple(
        _effect(order, FeatureType.EXPRESSION if order <= 50 else FeatureType.MUTATION_PRESENCE)
        for order in range(1, 69)
    )


def test_r8_constants_and_direction_values_are_frozen() -> None:
    assert COEF_EPS == 1e-6
    assert tuple(item.value for item in FeatureType) == ("expression", "mutation_presence")
    assert tuple(item.value for item in EffectDirection) == (
        "associated_with_higher_modeled_hazard",
        "associated_with_lower_modeled_hazard",
        "effectively_zero_under_r8_threshold",
    )
    assert DIRECTION_DISPLAY_TEXT == {
        EffectDirection.HIGHER: "Associated with higher modeled hazard",
        EffectDirection.LOWER: "Associated with lower modeled hazard",
        EffectDirection.EFFECTIVELY_ZERO: (
            "Effectively zero under the R8 numerical coefficient threshold"
        ),
    }


def test_feature_effect_csv_columns_have_exact_approved_order() -> None:
    assert FEATURE_EFFECTS_CSV_COLUMNS == (
        "rank",
        "frozen_genomic_order",
        "raw_feature_name",
        "model_feature_name",
        "feature_type",
        "beta",
        "abs_beta",
        "hazard_ratio",
        "direction",
        "direction_display",
        "is_active",
        "standard_error",
        "beta_ci_lower_95",
        "beta_ci_upper_95",
        "hazard_ratio_ci_lower_95",
        "hazard_ratio_ci_upper_95",
        "comparison_to",
        "z_statistic",
        "p_value",
        "negative_log2_p_value",
    )


def test_mapping_accepts_only_expression_or_mutation_presence() -> None:
    mapping = GenomicFeatureMapping(1, "brca1", "brca1", FeatureType.EXPRESSION)
    assert mapping.to_dict()["feature_type"] == "expression"
    with pytest.raises((TypeError, ValueError)):
        GenomicFeatureMapping(1, "brca1", "brca1", "clinical")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="positive"):
        replace(mapping, frozen_genomic_order=0)


def test_effect_contract_rejects_nonfinite_values_and_inconsistent_activity() -> None:
    effect = _effect(1, FeatureType.EXPRESSION)
    with pytest.raises(ValueError, match="finite"):
        replace(effect, beta=math.nan)
    with pytest.raises(ValueError, match="positive"):
        replace(effect, hazard_ratio=0.0)
    with pytest.raises(ValueError, match="abs_beta"):
        replace(effect, abs_beta=99.0)
    with pytest.raises(ValueError, match="activity"):
        replace(effect, is_active=False)
    with pytest.raises(ValueError, match="direction"):
        replace(effect, direction=EffectDirection.LOWER)


def test_analysis_result_requires_exactly_68_unique_nonclinical_effects() -> None:
    effects = _complete_effects()
    result = PrognosticFeatureAnalysisResult(
        schema_version="1.0",
        analysis_id="r8-test",
        coef_eps=COEF_EPS,
        effects=effects,
    )
    assert len(result.effects) == 68
    assert sum(effect.feature_type is FeatureType.EXPRESSION for effect in effects) == 50
    assert sum(effect.feature_type is FeatureType.MUTATION_PRESENCE for effect in effects) == 18
    with pytest.raises(ValueError, match="68"):
        replace(result, effects=effects[:-1])
    with pytest.raises(ValueError, match="unique"):
        replace(result, effects=effects[:-1] + (effects[-2],))
    with pytest.raises(ValueError, match="consecutive"):
        replace(result, effects=(replace(effects[0], rank=69),) + effects[1:])


def test_contract_vocabulary_excludes_selected_by_lasso() -> None:
    forbidden = "selected_by_lasso"
    assert forbidden not in FEATURE_EFFECTS_CSV_COLUMNS
    assert forbidden not in PrognosticFeatureEffect.__dataclass_fields__
    assert forbidden not in PrognosticFeatureAnalysisResult.__dataclass_fields__
