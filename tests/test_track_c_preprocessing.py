from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from src.data import load_track_c_feature_contract
from src.preprocessing.track_c import build_track_c_preprocessor, track_c_feature_names


ROOT = Path(__file__).resolve().parents[1]


def _frame(rows: int = 4) -> pd.DataFrame:
    contract = load_track_c_feature_contract(ROOT)
    values: dict[str, object] = {}
    for index, name in enumerate(contract.expression_features):
        values[name] = [float(index + row) for row in range(rows)]
    for index, name in enumerate(contract.mutation_features):
        column = ["0"] * rows
        if rows > 1 and index % 2 == 0:
            column[1] = "E883K"
        values[name] = column
    return pd.DataFrame(values, columns=list(contract.raw_features))


@pytest.mark.parametrize("scale_expression", [True, False])
def test_track_c_preprocessor_has_exact_stable_order_and_binary_mutations(
    scale_expression: bool,
) -> None:
    contract = load_track_c_feature_contract(ROOT)
    source = _frame()
    snapshot = source.copy(deep=True)
    preprocessor = build_track_c_preprocessor(contract, scale_expression=scale_expression)

    transformed = preprocessor.fit_transform(source)
    names = track_c_feature_names(preprocessor)

    assert transformed.shape == (4, 68)
    assert names[:50] == contract.expression_features
    assert names[50:] == tuple(f"{name}_present" for name in contract.mutation_features)
    assert set(np.unique(transformed[:, 50:])).issubset({0.0, 1.0})
    assert_frame_equal(source, snapshot)


def test_lr_and_svm_style_preprocessing_scales_expression_from_train_only() -> None:
    contract = load_track_c_feature_contract(ROOT)
    train = _frame()
    holdout = _frame()
    holdout.loc[:, list(contract.expression_features)] += 1000.0
    preprocessor = build_track_c_preprocessor(contract, scale_expression=True)

    train_values = preprocessor.fit_transform(train)
    scaler = preprocessor.named_steps["columns"].named_transformers_["expression"]
    learned_mean = scaler.mean_.copy()
    holdout_values = preprocessor.transform(holdout)

    np.testing.assert_allclose(train_values[:, :50].mean(axis=0), 0.0, atol=1e-12)
    np.testing.assert_array_equal(scaler.mean_, learned_mean)
    assert np.all(holdout_values[:, :50] > 100.0)


def test_rf_and_gb_style_preprocessing_keeps_expression_unscaled() -> None:
    contract = load_track_c_feature_contract(ROOT)
    source = _frame()
    preprocessor = build_track_c_preprocessor(contract, scale_expression=False)

    transformed = preprocessor.fit_transform(source)

    np.testing.assert_array_equal(
        transformed[:, :50],
        source.loc[:, list(contract.expression_features)].to_numpy(dtype=float),
    )


def test_track_c_preprocessor_reuses_r4d_mapper_and_rejects_malformed_annotations() -> None:
    contract = load_track_c_feature_contract(ROOT)
    source = _frame()
    source.loc[0, contract.mutation_features[0]] = True
    preprocessor = build_track_c_preprocessor(contract, scale_expression=False)

    with pytest.raises(ValueError, match="invalid mutation annotation"):
        preprocessor.fit_transform(source)


def test_track_c_guard_rejects_missing_unexpected_and_null_expression_columns() -> None:
    contract = load_track_c_feature_contract(ROOT)
    source = _frame()
    preprocessor = build_track_c_preprocessor(contract, scale_expression=True)

    with pytest.raises(ValueError, match="missing columns"):
        preprocessor.fit(source.drop(columns=[contract.expression_features[0]]))
    with pytest.raises(ValueError, match="unexpected columns"):
        preprocessor.fit(source.assign(age_at_diagnosis=55.0))
    source.loc[0, contract.expression_features[0]] = np.nan
    with pytest.raises(ValueError, match="without an approved imputation policy"):
        preprocessor.fit(source)
