from __future__ import annotations

from dataclasses import replace
import math
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.analysis.prognostic_features import (
    build_genomic_feature_mapping,
    extract_prognostic_feature_effects,
    summarize_prognostic_feature_effects,
)
from src.artifacts.prognostic_features import verify_and_load_track_b_source
from src.contracts import EffectDirection, PrognosticFeatureEffect


@pytest.fixture(scope="module")
def source():
    root = Path(__file__).resolve().parents[1]
    return verify_and_load_track_b_source(root / "artifacts/models/track_b/r6-track-b-v1", root)


def _mapping(source):
    return build_genomic_feature_mapping(source.feature_contract, source.model_feature_names)


def _mutate(source, betas=None, summary_updates=None):
    params = source.model.fitter.params_.copy().astype(object)
    summary = source.model.fitter.summary.copy().astype(object)
    for name, beta in (betas or {}).items():
        params.loc[name] = beta
        summary.loc[name, "coef"] = beta
        if isinstance(beta, (int, float)) and not isinstance(beta, bool) and math.isfinite(beta):
            summary.loc[name, "exp(coef)"] = math.exp(beta)
    for name, column, value in summary_updates or ():
        summary.loc[name, column] = value
    model = SimpleNamespace(fitter=SimpleNamespace(params_=params, summary=summary))
    return replace(source, model=model)


def test_all_nine_model_reported_summary_fields_are_preserved(source) -> None:
    mapping = _mapping(source)
    result = extract_prognostic_feature_effects(source, mapping)
    effect = next(item for item in result.effects if item.model_feature_name == mapping[0].model_feature_name)
    row = source.model.fitter.summary.loc[mapping[0].model_feature_name]
    assert effect.model_summary.to_dict() == {
        "standard_error": row["se(coef)"],
        "beta_ci_lower_95": row["coef lower 95%"],
        "beta_ci_upper_95": row["coef upper 95%"],
        "hazard_ratio_ci_lower_95": row["exp(coef) lower 95%"],
        "hazard_ratio_ci_upper_95": row["exp(coef) upper 95%"],
        "comparison_to": row["cmp to"],
        "z_statistic": row["z"],
        "p_value": row["p"],
        "negative_log2_p_value": row["-log2(p)"],
    }


@pytest.mark.parametrize(
    ("column", "value"),
    (("se(coef)", math.nan), ("coef lower 95%", 2.0)),
)
def test_nonfinite_summary_value_or_incoherent_ci_is_rejected(source, column, value) -> None:
    mapping = _mapping(source)
    name = mapping[0].model_feature_name
    updates = [(name, column, value)]
    if column == "coef lower 95%":
        updates.append((name, "coef upper 95%", 1.0))
    with pytest.raises(ValueError, match="finite|bounds|interval"):
        extract_prognostic_feature_effects(_mutate(source, summary_updates=updates), mapping)


@pytest.mark.parametrize(
    ("lower", "upper"),
    ((0.0, 1.0), (1.0, math.inf), (2.0, 1.0)),
)
def test_hazard_ratio_ci_must_be_finite_positive_and_ordered(source, lower, upper) -> None:
    mapping = _mapping(source)
    name = mapping[0].model_feature_name
    mutated = _mutate(
        source,
        summary_updates=[
            (name, "exp(coef) lower 95%", lower),
            (name, "exp(coef) upper 95%", upper),
        ],
    )
    with pytest.raises(ValueError, match="finite|positive|bounds|interval"):
        extract_prognostic_feature_effects(mutated, mapping)


def test_exact_abs_beta_ties_follow_frozen_genomic_order(source) -> None:
    mapping = _mapping(source)
    names = (mapping[0].model_feature_name, mapping[1].model_feature_name)
    result = extract_prognostic_feature_effects(
        _mutate(source, betas={names[0]: 0.75, names[1]: -0.75}), mapping
    )
    tied = [effect for effect in result.effects if effect.model_feature_name in names]
    assert [effect.model_feature_name for effect in tied] == list(names)


def test_ranks_are_consecutive_one_through_sixty_eight(source) -> None:
    result = extract_prognostic_feature_effects(source, _mapping(source))
    assert tuple(effect.rank for effect in result.effects) == tuple(range(1, 69))


def test_p_value_changes_cannot_change_rank_or_activity(source) -> None:
    mapping = _mapping(source)
    name = mapping[0].model_feature_name
    low = extract_prognostic_feature_effects(
        _mutate(
            source,
            summary_updates=[(name, "p", 1e-12), (name, "-log2(p)", -math.log2(1e-12))],
        ),
        mapping,
    )
    high = extract_prognostic_feature_effects(
        _mutate(
            source,
            summary_updates=[(name, "p", 0.9), (name, "-log2(p)", -math.log2(0.9))],
        ),
        mapping,
    )
    assert [(e.model_feature_name, e.rank, e.is_active) for e in low.effects] == [
        (e.model_feature_name, e.rank, e.is_active) for e in high.effects
    ]


def test_activity_feature_type_and_ci_cannot_filter_or_reorder_rows(source) -> None:
    mapping = _mapping(source)
    result = extract_prognostic_feature_effects(source, mapping)
    summary = summarize_prognostic_feature_effects(result)
    assert len(result.effects) == 68
    assert summary["total"] == 68
    assert summary["feature_type_counts"] == {"expression": 50, "mutation_presence": 18}


def test_all_effectively_zero_rows_remain_in_full_table(source) -> None:
    mapping = _mapping(source)
    betas = {item.model_feature_name: 0.0 for item in mapping}
    result = extract_prognostic_feature_effects(_mutate(source, betas=betas), mapping)
    assert len(result.effects) == 68
    assert all(effect.direction is EffectDirection.EFFECTIVELY_ZERO for effect in result.effects)
    assert summarize_prognostic_feature_effects(result)["activity_counts"] == {
        "active": 0,
        "effectively_zero": 68,
    }


def test_analysis_produces_no_significance_classification(source) -> None:
    result = extract_prognostic_feature_effects(source, _mapping(source))
    summary = summarize_prognostic_feature_effects(result)
    vocabulary = repr(result.to_dict()).lower() + repr(summary).lower()
    assert "significant" not in vocabulary
    assert "selected_by_lasso" not in vocabulary
    assert "top_n" not in vocabulary
    assert "significance" not in PrognosticFeatureEffect.__dataclass_fields__
