from __future__ import annotations

from dataclasses import replace
import math
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from src.analysis.prognostic_features import (
    build_genomic_feature_mapping,
    extract_prognostic_feature_effects,
)
from src.artifacts.prognostic_features import verify_and_load_track_b_source
from src.contracts import COEF_EPS, EffectDirection


@pytest.fixture(scope="module")
def canonical_source():
    root = Path(__file__).resolve().parents[1]
    return verify_and_load_track_b_source(root / "artifacts/models/track_b/r6-track-b-v1", root)


def _mapping(source):
    return build_genomic_feature_mapping(source.feature_contract, source.model_feature_names)


def _source_with_betas(source, updates: dict[str, object], *, shuffle_summary: bool = False):
    params = source.model.fitter.params_.copy().astype(object)
    summary = source.model.fitter.summary.copy().astype(object)
    for name, beta in updates.items():
        params.loc[name] = beta
        summary.loc[name, "coef"] = beta
        if isinstance(beta, bool):
            summary.loc[name, "exp(coef)"] = math.exp(float(beta))
        elif isinstance(beta, (int, float)) and math.isfinite(beta) and beta < 710:
            summary.loc[name, "exp(coef)"] = math.exp(beta)
    if shuffle_summary:
        summary = summary.sample(frac=1.0, random_state=42)
    model = SimpleNamespace(fitter=SimpleNamespace(params_=params, summary=summary))
    return replace(source, model=model)


def _by_name(result):
    return {effect.model_feature_name: effect for effect in result.effects}


def test_positive_negative_zero_and_near_threshold_coefficients(canonical_source) -> None:
    mapping = _mapping(canonical_source)
    values = (0.5, -0.5, 0.0, 0.5e-6, -0.5e-6)
    updates = {mapping[index].model_feature_name: value for index, value in enumerate(values)}
    result = extract_prognostic_feature_effects(_source_with_betas(canonical_source, updates), mapping)
    effects = _by_name(result)
    assert effects[mapping[0].model_feature_name].direction is EffectDirection.HIGHER
    assert effects[mapping[1].model_feature_name].direction is EffectDirection.LOWER
    for item in mapping[2:5]:
        assert effects[item.model_feature_name].direction is EffectDirection.EFFECTIVELY_ZERO
        assert effects[item.model_feature_name].is_active is False


@pytest.mark.parametrize("beta", (1e-6, -1e-6))
def test_activity_and_direction_are_inclusive_at_both_exact_boundaries(canonical_source, beta) -> None:
    mapping = _mapping(canonical_source)
    name = mapping[0].model_feature_name
    result = extract_prognostic_feature_effects(
        _source_with_betas(canonical_source, {name: beta}), mapping
    )
    effect = _by_name(result)[name]
    assert effect.is_active is False
    assert effect.direction is EffectDirection.EFFECTIVELY_ZERO


@pytest.mark.parametrize(
    ("beta", "direction"),
    (
        (math.nextafter(1e-6, math.inf), EffectDirection.HIGHER),
        (math.nextafter(-1e-6, -math.inf), EffectDirection.LOWER),
    ),
)
def test_values_immediately_outside_threshold_are_active(canonical_source, beta, direction) -> None:
    mapping = _mapping(canonical_source)
    name = mapping[0].model_feature_name
    effect = _by_name(
        extract_prognostic_feature_effects(
            _source_with_betas(canonical_source, {name: beta}), mapping
        )
    )[name]
    assert effect.is_active is True
    assert effect.direction is direction


def test_extraction_joins_params_and_summary_by_exact_name_not_position(canonical_source) -> None:
    mapping = _mapping(canonical_source)
    source = _source_with_betas(
        canonical_source,
        {mapping[0].model_feature_name: 0.5, mapping[1].model_feature_name: -0.5},
        shuffle_summary=True,
    )
    effects = _by_name(extract_prognostic_feature_effects(source, mapping))
    assert effects[mapping[0].model_feature_name].beta == 0.5
    assert effects[mapping[1].model_feature_name].beta == -0.5


@pytest.mark.parametrize("mode", ("missing", "duplicate"))
def test_missing_or_duplicate_summary_row_is_rejected(canonical_source, mode) -> None:
    mapping = _mapping(canonical_source)
    params = canonical_source.model.fitter.params_.copy()
    summary = canonical_source.model.fitter.summary.copy()
    if mode == "missing":
        summary = summary.drop(index=mapping[0].model_feature_name)
    else:
        summary = pd.concat([summary, summary.loc[[mapping[0].model_feature_name]]])
    source = replace(
        canonical_source,
        model=SimpleNamespace(fitter=SimpleNamespace(params_=params, summary=summary)),
    )
    with pytest.raises(ValueError, match="summary"):
        extract_prognostic_feature_effects(source, mapping)


@pytest.mark.parametrize("beta", (True, math.nan, math.inf, -math.inf))
def test_bool_nan_and_infinite_beta_are_rejected(canonical_source, beta) -> None:
    mapping = _mapping(canonical_source)
    source = _source_with_betas(canonical_source, {mapping[0].model_feature_name: beta})
    with pytest.raises(ValueError, match="finite real"):
        extract_prognostic_feature_effects(source, mapping)


@pytest.mark.parametrize("reported", (0.0, math.inf, math.nan))
def test_exp_overflow_and_nonpositive_or_nonfinite_hazard_ratio_are_rejected(
    canonical_source, reported
) -> None:
    mapping = _mapping(canonical_source)
    name = mapping[0].model_feature_name
    if reported == 0.0:
        source = _source_with_betas(canonical_source, {name: 1000.0})
        with pytest.raises(ValueError, match="overflowed"):
            extract_prognostic_feature_effects(source, mapping)
    else:
        source = _source_with_betas(canonical_source, {name: 0.5})
        source.model.fitter.summary.loc[name, "exp(coef)"] = reported
        with pytest.raises(ValueError, match="hazard ratio"):
            extract_prognostic_feature_effects(source, mapping)


def test_derived_hazard_ratio_matches_exp_beta_and_model_report(canonical_source) -> None:
    mapping = _mapping(canonical_source)
    name = mapping[0].model_feature_name
    source = _source_with_betas(canonical_source, {name: 0.5})
    effect = _by_name(extract_prognostic_feature_effects(source, mapping))[name]
    assert effect.hazard_ratio == pytest.approx(math.exp(0.5), rel=1e-12)
    source.model.fitter.summary.loc[name, "exp(coef)"] += 1e-4
    with pytest.raises(ValueError, match="model-reported"):
        extract_prognostic_feature_effects(source, mapping)
