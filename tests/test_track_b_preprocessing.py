"""R6 explicit Track B feature-contract and preprocessing tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from src.data.metabric import MetabricPaths
from src.preprocessing.pipelines import build_clinical_survival_preprocessor
from src.preprocessing.schema import load_preprocessing_schema
from src.preprocessing.track_b import (
    SelectedMutationPresenceTransformer,
    build_track_b_preprocessor,
    load_track_b_feature_contract,
    track_b_feature_names,
)


ROOT = Path(__file__).resolve().parents[1]
CLINICAL = (
    "age_at_diagnosis",
    "tumor_size",
    "tumor_stage",
    "lymph_nodes_examined_positive",
    "er_status_measured_by_ihc",
    "pr_status",
    "her2_status",
)


def _frame(contract, rows: int = 4) -> pd.DataFrame:
    values: dict[str, object] = {
        "age_at_diagnosis": [40.0, 50.0, 60.0, 70.0][:rows],
        "tumor_size": [10.0, np.nan, 30.0, 40.0][:rows],
        "tumor_stage": ["1", "2", "3", "Unknown"][:rows],
        "lymph_nodes_examined_positive": [0, 1, 2, 3][:rows],
        "er_status_measured_by_ihc": ["Negative", "Positive", np.nan, "Negative"][:rows],
        "pr_status": ["Negative", "Positive", "Negative", "Positive"][:rows],
        "her2_status": ["Negative", "Positive", "Negative", "Positive"][:rows],
    }
    for index, name in enumerate(contract.expression_features):
        values[name] = [float(index + row) for row in range(rows)]
    for index, name in enumerate(contract.mutation_features):
        column = ["0"] * rows
        if rows > 1 and index % 2 == 0:
            column[1] = "p.V600E"
        values[name] = column
    return pd.DataFrame(values, columns=list(contract.raw_features))


def test_canonical_track_b_contract_is_explicit_and_exact() -> None:
    contract = load_track_b_feature_contract(ROOT)

    assert contract.clinical_features == CLINICAL
    assert len(contract.expression_features) == 50
    assert len(contract.mutation_features) == 18
    assert len(contract.raw_features) == 75
    assert contract.raw_features == (
        contract.clinical_features
        + contract.expression_features
        + contract.mutation_features
    )
    assert all(name.endswith("_mut") for name in contract.mutation_features)
    assert not set(contract.expression_features) & set(contract.mutation_features)


def test_contract_rejects_duplicate_or_wrong_count_selected_features(tmp_path: Path) -> None:
    canonical = (ROOT / "ai_handoff_data" / "v1" / "selected_features.txt").read_text(
        encoding="utf-8"
    ).splitlines()
    duplicate = tmp_path / "duplicate.txt"
    duplicate.write_text("\n".join([*canonical, canonical[0]]) + "\n", encoding="utf-8")
    missing = tmp_path / "missing.txt"
    missing.write_text("\n".join(canonical[:-1]) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate"):
        load_track_b_feature_contract(ROOT, selected_features_path=duplicate)
    with pytest.raises(ValueError, match="18 mutation"):
        load_track_b_feature_contract(ROOT, selected_features_path=missing)


def test_composite_preprocessor_matches_frozen_r5_clinical_and_emits_80_features() -> None:
    schema = load_preprocessing_schema(MetabricPaths.from_repository_root(ROOT))
    contract = load_track_b_feature_contract(ROOT)
    train = _frame(contract)
    source = train.copy(deep=True)

    track_b = build_track_b_preprocessor(schema, contract)
    transformed = track_b.fit_transform(train)
    names = track_b_feature_names(track_b)
    r5 = build_clinical_survival_preprocessor(schema)
    r5_values = r5.fit_transform(train.loc[:, list(CLINICAL)])

    assert transformed.shape == (4, 80)
    assert len(names) == len(set(names)) == 80
    np.testing.assert_allclose(transformed[:, :12], r5_values)
    assert names[:12] == tuple(r5.get_feature_names_out())
    assert names[12:62] == contract.expression_features
    assert names[62:] == tuple(f"{name}_present" for name in contract.mutation_features)
    assert_frame_equal(train, source)


def test_expression_scaler_fits_train_only_and_preserves_selected_order() -> None:
    schema = load_preprocessing_schema(MetabricPaths.from_repository_root(ROOT))
    contract = load_track_b_feature_contract(ROOT)
    train = _frame(contract)
    holdout = _frame(contract)
    holdout.loc[:, list(contract.expression_features)] += 1000.0
    preprocessor = build_track_b_preprocessor(schema, contract)

    preprocessor.fit_transform(train)
    scaler = preprocessor.named_steps["columns"].named_transformers_["expression"]
    train_mean = scaler.mean_.copy()
    preprocessor.transform(holdout)

    np.testing.assert_array_equal(scaler.mean_, train_mean)
    assert tuple(scaler.feature_names_in_) == contract.expression_features
    assert track_b_feature_names(preprocessor)[12:62] == contract.expression_features


def test_selected_mutations_use_r4d_semantics_and_reject_malformed_values() -> None:
    transformer = SelectedMutationPresenceTransformer(("a_mut", "b_mut"))
    source = pd.DataFrame({"a_mut": ["0", " p.V600E "], "b_mut": [0, -2.5]})
    snapshot = source.copy(deep=True)

    transformed = transformer.fit_transform(source)

    np.testing.assert_array_equal(transformed, [[0.0, 0.0], [1.0, 1.0]])
    assert set(np.unique(transformed)) == {0.0, 1.0}
    assert tuple(transformer.get_feature_names_out()) == ("a_mut_present", "b_mut_present")
    assert not hasattr(transformer, "prevalence_")
    assert_frame_equal(source, snapshot)

    with pytest.raises(ValueError, match="invalid mutation annotation"):
        transformer.transform(pd.DataFrame({"a_mut": [True], "b_mut": ["0"]}))
    with pytest.raises(ValueError, match="missing mutation annotation"):
        transformer.transform(pd.DataFrame({"a_mut": [None], "b_mut": ["0"]}))
