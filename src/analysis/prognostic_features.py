"""Explicit frozen R6 genomic feature mapping for R8 analysis."""

from __future__ import annotations

from dataclasses import replace
import math
from numbers import Real
from typing import Mapping

from src.artifacts.prognostic_features import VerifiedTrackBSource
from src.contracts import (
    COEF_EPS,
    DIRECTION_DISPLAY_TEXT,
    EffectDirection,
    FeatureType,
    GenomicFeatureMapping,
    PenalizedCoxSummaryValues,
    PrognosticFeatureAnalysisResult,
    PrognosticFeatureEffect,
)
from src.preprocessing.track_b import track_b_feature_names


R6_CLINICAL_MODEL_FEATURES = (
    "age_at_diagnosis",
    "tumor_size",
    "lymph_nodes_examined_positive",
    "tumor_stage_2",
    "tumor_stage_3",
    "tumor_stage_4",
    "tumor_stage_Unknown",
    "er_status_measured_by_ihc_Positive",
    "pr_status_Positive",
    "her2_status_Positive",
    "tumor_size_was_missing",
    "er_status_measured_by_ihc_was_missing",
)


def _ordered_unique_names(contract: Mapping[str, object], key: str, expected: int) -> tuple[str, ...]:
    values = contract.get(key)
    if not isinstance(values, (list, tuple)) or len(values) != expected:
        label = "expression" if key == "expression_features" else "mutation"
        raise ValueError(f"R8 requires exactly {expected} {label} features")
    names = tuple(values)
    if any(not isinstance(name, str) or not name.strip() for name in names):
        raise ValueError(f"{key} must contain non-empty names")
    if len(names) != len(set(names)):
        raise ValueError(f"{key} must contain unique names")
    return names


def build_genomic_feature_mapping(
    feature_contract: Mapping[str, object],
    model_feature_names: tuple[str, ...],
) -> tuple[GenomicFeatureMapping, ...]:
    """Map only the explicit R6 expression and mutation contract in frozen order."""
    expression_names = _ordered_unique_names(feature_contract, "expression_features", 50)
    mutation_names = _ordered_unique_names(feature_contract, "mutation_features", 18)
    if set(expression_names) & set(mutation_names):
        raise ValueError("expression and mutation feature groups must be disjoint")
    if len(model_feature_names) != 80:
        raise ValueError("R6 fitted model must contain exactly 80 names")
    if len(model_feature_names) != len(set(model_feature_names)):
        raise ValueError("R6 fitted model names must be unique")
    expression = tuple(
        GenomicFeatureMapping(i, raw, raw, FeatureType.EXPRESSION)
        for i, raw in enumerate(expression_names, start=1)
    )
    mutation = tuple(
        GenomicFeatureMapping(i, raw, f"{raw}_present", FeatureType.MUTATION_PRESENCE)
        for i, raw in enumerate(mutation_names, start=51)
    )
    mapping = expression + mutation
    mapped_names = tuple(item.model_feature_name for item in mapping)
    if model_feature_names[:12] != R6_CLINICAL_MODEL_FEATURES:
        raise ValueError("R6 clinical encoded prefix is not the frozen 12-feature authority")
    if model_feature_names[12:] != mapped_names:
        raise ValueError("R6 fitted names do not match the explicit mapped genomic order")
    return mapping


def validate_genomic_mapping_authorities(
    mapping: tuple[GenomicFeatureMapping, ...],
    source: VerifiedTrackBSource,
) -> None:
    """Require persisted, preprocessor, adapter, params, and summary orders to agree."""
    expected_mapping = build_genomic_feature_mapping(source.feature_contract, source.model_feature_names)
    if mapping != expected_mapping:
        raise ValueError("genomic mapping differs from the persisted feature-contract authority")
    expected = R6_CLINICAL_MODEL_FEATURES + tuple(item.model_feature_name for item in mapping)
    authorities = {
        "persisted": source.model_feature_names,
        "preprocessor": track_b_feature_names(source.preprocessor),
        "adapter": tuple(source.model.feature_names),
        "params": tuple(source.model.fitter.params_.index),
        "summary": tuple(source.model.fitter.summary.index),
    }
    mismatches = [name for name, values in authorities.items() if tuple(values) != expected]
    if mismatches:
        raise ValueError(f"R6 fitted feature-order authority mismatch: {', '.join(mismatches)}")


def _finite_real(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValueError(f"{field_name} must be a finite real number")
    return float(value)


def _direction(beta: float, coef_eps: float) -> EffectDirection:
    if beta > coef_eps:
        return EffectDirection.HIGHER
    if beta < -coef_eps:
        return EffectDirection.LOWER
    return EffectDirection.EFFECTIVELY_ZERO


def _hazard_ratio(beta: float) -> float:
    beta = _finite_real(beta, "beta")
    try:
        value = math.exp(beta)
    except OverflowError as error:
        raise ValueError("hazard ratio overflowed") from error
    if not math.isfinite(value) or value <= 0:
        raise ValueError("hazard ratio must be finite and positive")
    return value


def _summary_values(row) -> PenalizedCoxSummaryValues:
    return PenalizedCoxSummaryValues(
        standard_error=_finite_real(row["se(coef)"], "standard_error"),
        beta_ci_lower_95=_finite_real(row["coef lower 95%"], "beta_ci_lower_95"),
        beta_ci_upper_95=_finite_real(row["coef upper 95%"], "beta_ci_upper_95"),
        hazard_ratio_ci_lower_95=_finite_real(
            row["exp(coef) lower 95%"], "hazard_ratio_ci_lower_95"
        ),
        hazard_ratio_ci_upper_95=_finite_real(
            row["exp(coef) upper 95%"], "hazard_ratio_ci_upper_95"
        ),
        comparison_to=_finite_real(row["cmp to"], "comparison_to"),
        z_statistic=_finite_real(row["z"], "z_statistic"),
        p_value=_finite_real(row["p"], "p_value"),
        negative_log2_p_value=_finite_real(row["-log2(p)"], "negative_log2_p_value"),
    )


def extract_prognostic_feature_effects(
    source: VerifiedTrackBSource,
    mapping: tuple[GenomicFeatureMapping, ...],
    coef_eps: float = COEF_EPS,
) -> PrognosticFeatureAnalysisResult:
    """Extract and rank all mapped genomic coefficients without fitting or patient data."""
    if coef_eps != COEF_EPS:
        raise ValueError("R8 coefficient threshold is frozen at COEF_EPS")
    expected_mapping = build_genomic_feature_mapping(source.feature_contract, source.model_feature_names)
    if mapping != expected_mapping:
        raise ValueError("genomic mapping differs from the persisted feature-contract authority")
    params = source.model.fitter.params_
    summary = source.model.fitter.summary
    if params.index.has_duplicates:
        raise ValueError("Cox params index contains duplicate names")
    if summary.index.has_duplicates:
        raise ValueError("Cox summary index contains duplicate names")
    names = tuple(item.model_feature_name for item in mapping)
    missing_params = [name for name in names if name not in params.index]
    missing_summary = [name for name in names if name not in summary.index]
    if missing_params:
        raise ValueError(f"Cox params are missing mapped rows: {missing_params}")
    if missing_summary:
        raise ValueError(f"Cox summary is missing mapped rows: {missing_summary}")

    effects: list[PrognosticFeatureEffect] = []
    for item in mapping:
        name = item.model_feature_name
        beta = _finite_real(params.loc[name], "beta")
        hazard_ratio = _hazard_ratio(beta)
        row = summary.loc[name]
        model_reported_hazard_ratio = _finite_real(row["exp(coef)"], "model-reported hazard ratio")
        if model_reported_hazard_ratio <= 0:
            raise ValueError("model-reported hazard ratio must be finite and positive")
        if not math.isclose(
            hazard_ratio,
            model_reported_hazard_ratio,
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise ValueError("derived hazard ratio does not match model-reported hazard ratio")
        direction = _direction(beta, coef_eps)
        effects.append(
            PrognosticFeatureEffect(
                rank=1,
                frozen_genomic_order=item.frozen_genomic_order,
                raw_feature_name=item.raw_feature_name,
                model_feature_name=name,
                feature_type=item.feature_type,
                beta=beta,
                abs_beta=abs(beta),
                hazard_ratio=hazard_ratio,
                direction=direction,
                direction_display=DIRECTION_DISPLAY_TEXT[direction],
                is_active=abs(beta) > coef_eps,
                model_summary=_summary_values(row),
            )
        )
    ordered = sorted(effects, key=lambda effect: (-effect.abs_beta, effect.frozen_genomic_order))
    ranked = tuple(replace(effect, rank=rank) for rank, effect in enumerate(ordered, start=1))
    return PrognosticFeatureAnalysisResult(
        schema_version="1.0",
        analysis_id="r8-prognostic-features-v1",
        coef_eps=coef_eps,
        effects=ranked,
    )


def summarize_prognostic_feature_effects(
    result: PrognosticFeatureAnalysisResult,
) -> dict[str, object]:
    """Return aggregate counts only; never select, filter, or classify significance."""
    if not isinstance(result, PrognosticFeatureAnalysisResult):
        raise TypeError("result must be PrognosticFeatureAnalysisResult")
    return {
        "total": len(result.effects),
        "feature_type_counts": {
            feature_type.value: sum(
                effect.feature_type is feature_type for effect in result.effects
            )
            for feature_type in FeatureType
        },
        "activity_counts": {
            "active": sum(effect.is_active for effect in result.effects),
            "effectively_zero": sum(not effect.is_active for effect in result.effects),
        },
        "direction_counts": {
            direction.value: sum(effect.direction is direction for effect in result.effects)
            for direction in EffectDirection
        },
    }
