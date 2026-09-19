from __future__ import annotations

import copy
from dataclasses import replace
import inspect
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from src.analysis import prognostic_features as mapping_module
from src.analysis.prognostic_features import (
    build_genomic_feature_mapping,
    validate_genomic_mapping_authorities,
)
from src.artifacts.prognostic_features import verify_and_load_track_b_source
from src.contracts import FeatureType


@pytest.fixture(scope="module")
def source():
    root = Path(__file__).resolve().parents[1]
    return verify_and_load_track_b_source(
        root / "artifacts/models/track_b/r6-track-b-v1", root
    )


def _contract(source) -> dict[str, object]:
    return copy.deepcopy(dict(source.feature_contract))


def test_mapping_is_exactly_50_expression_18_mutation_and_zero_clinical(source) -> None:
    mapping = build_genomic_feature_mapping(source.feature_contract, source.model_feature_names)
    assert len(mapping) == 68
    assert sum(item.feature_type is FeatureType.EXPRESSION for item in mapping) == 50
    assert sum(item.feature_type is FeatureType.MUTATION_PRESENCE for item in mapping) == 18
    assert not set(source.feature_contract["clinical_features"]) & {
        item.raw_feature_name for item in mapping
    }


def test_mutation_mapping_appends_present_to_each_raw_mut_name(source) -> None:
    mapping = build_genomic_feature_mapping(source.feature_contract, source.model_feature_names)
    mutations = mapping[50:]
    assert tuple(item.model_feature_name for item in mutations) == tuple(
        f"{name}_present" for name in source.feature_contract["mutation_features"]
    )


@pytest.mark.parametrize("delta", (-1, 1))
def test_mapping_rejects_79_or_81_fitted_model_names(source, delta) -> None:
    names = source.model_feature_names[: 80 + delta] if delta < 0 else source.model_feature_names + ("extra",)
    with pytest.raises(ValueError, match="80"):
        build_genomic_feature_mapping(source.feature_contract, names)


@pytest.mark.parametrize("group,delta", (("expression_features", -1), ("mutation_features", 1)))
def test_mapping_rejects_67_or_69_genomic_features(source, group, delta) -> None:
    contract = _contract(source)
    values = list(contract[group])
    contract[group] = values[:-1] if delta < 0 else values + ["extra_mut"]
    with pytest.raises(ValueError, match="50 expression|18 mutation"):
        build_genomic_feature_mapping(contract, source.model_feature_names)


def test_mapping_rejects_duplicate_raw_or_model_name(source) -> None:
    contract = _contract(source)
    contract["expression_features"][1] = contract["expression_features"][0]
    with pytest.raises(ValueError, match="unique"):
        build_genomic_feature_mapping(contract, source.model_feature_names)
    names = list(source.model_feature_names)
    names[-1] = names[-2]
    with pytest.raises(ValueError, match="unique"):
        build_genomic_feature_mapping(source.feature_contract, tuple(names))


def test_mapping_rejects_expression_mutation_collision(source) -> None:
    contract = _contract(source)
    contract["mutation_features"][0] = contract["expression_features"][0]
    with pytest.raises(ValueError, match="disjoint"):
        build_genomic_feature_mapping(contract, source.model_feature_names)


def test_mapping_rejects_missing_or_additional_model_name(source) -> None:
    names = list(source.model_feature_names)
    names[-1] = "unexpected_mut_present"
    with pytest.raises(ValueError, match="mapped genomic"):
        build_genomic_feature_mapping(source.feature_contract, tuple(names))


def test_mapping_rejects_reordered_authority_even_when_counts_match(source) -> None:
    names = list(source.model_feature_names)
    names[-1], names[-2] = names[-2], names[-1]
    with pytest.raises(ValueError, match="mapped genomic"):
        build_genomic_feature_mapping(source.feature_contract, tuple(names))


@pytest.mark.parametrize("authority", ("persisted", "preprocessor", "adapter", "params", "summary"))
def test_all_four_fitted_authorities_must_agree(source, authority, monkeypatch) -> None:
    mapping = build_genomic_feature_mapping(source.feature_contract, source.model_feature_names)
    mutated = source
    if authority == "persisted":
        names = list(source.model_feature_names)
        names[-1], names[-2] = names[-2], names[-1]
        mutated = replace(source, model_feature_names=tuple(names))
    elif authority == "preprocessor":
        monkeypatch.setattr(
            mapping_module,
            "track_b_feature_names",
            lambda value: source.model_feature_names[:-1] + ("wrong",),
        )
    else:
        model = SimpleNamespace(
            feature_names=source.model.feature_names,
            fitter=SimpleNamespace(
                params_=source.model.fitter.params_.copy(),
                summary=source.model.fitter.summary.copy(),
            ),
        )
        if authority == "adapter":
            model.feature_names = model.feature_names[:-1] + ("wrong",)
        elif authority == "params":
            model.fitter.params_.index = pd.Index(model.feature_names[:-1] + ("wrong",))
        else:
            model.fitter.summary.index = pd.Index(model.feature_names[:-1] + ("wrong",))
        mutated = replace(source, model=model)
    with pytest.raises(ValueError, match="authority|mapping|mapped genomic"):
        validate_genomic_mapping_authorities(mapping, mutated)


def test_mapping_uses_explicit_contract_not_dtype_or_prefix_discovery() -> None:
    text = inspect.getsource(mapping_module)
    assert "select_dtypes" not in text
    assert ".dtype" not in text
    assert "startswith" not in text
    assert "expression_features" in text
    assert "mutation_features" in text
