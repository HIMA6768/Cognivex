"""Small sklearn-compatible transformers shared by R4 task pipelines."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.utils.validation import check_is_fitted


class FeatureFrameGuard(TransformerMixin, BaseEstimator):
    """Validate and order an allowlisted task feature frame before transformation."""

    def __init__(self, expected_columns: tuple[str, ...], nullable_columns: tuple[str, ...] = ()) -> None:
        self.expected_columns = expected_columns
        self.nullable_columns = nullable_columns

    def _validate(self, frame: object) -> pd.DataFrame:
        if not isinstance(frame, pd.DataFrame):
            raise TypeError("preprocessing input must be a pandas DataFrame")
        missing = tuple(column for column in self.expected_columns if column not in frame.columns)
        unexpected = tuple(column for column in frame.columns if column not in self.expected_columns)
        if missing:
            raise ValueError(f"preprocessing input is missing columns: {', '.join(missing)}")
        if unexpected:
            raise ValueError(f"preprocessing input contains unexpected columns: {', '.join(unexpected)}")
        for column in self.expected_columns:
            if column not in self.nullable_columns and frame[column].isna().any():
                raise ValueError(f"{column} contains missing values without an approved imputation policy")
        return frame.loc[:, list(self.expected_columns)]

    def fit(self, X: object, y: object = None) -> "FeatureFrameGuard":
        frame = self._validate(X)
        self.n_features_in_ = frame.shape[1]
        self.feature_names_in_ = np.asarray(self.expected_columns, dtype=object)
        return self

    def transform(self, X: object) -> pd.DataFrame:
        check_is_fitted(self, "feature_names_in_")
        return self._validate(X)

    def get_feature_names_out(self, input_features: object = None) -> np.ndarray:
        check_is_fitted(self, "feature_names_in_")
        return self.feature_names_in_.copy()


class OriginalMissingIndicator(TransformerMixin, BaseEstimator):
    """Emit one exact-name indicator from the original pre-imputation column."""

    def __init__(self, feature_name: str, output_name: str) -> None:
        self.feature_name = feature_name
        self.output_name = output_name

    def fit(self, X: object, y: object = None) -> "OriginalMissingIndicator":
        values = self._values(X)
        self.n_features_in_ = 1
        self.feature_names_in_ = np.asarray([self.feature_name], dtype=object)
        if values.ndim != 1:
            raise ValueError("missing indicator requires exactly one input feature")
        return self

    def transform(self, X: object) -> np.ndarray:
        check_is_fitted(self, "feature_names_in_")
        values = self._values(X)
        return pd.isna(values).astype(float).reshape(-1, 1)

    def get_feature_names_out(self, input_features: object = None) -> np.ndarray:
        check_is_fitted(self, "feature_names_in_")
        return np.asarray([self.output_name], dtype=object)

    @staticmethod
    def _values(X: object) -> np.ndarray:
        if isinstance(X, pd.DataFrame):
            if X.shape[1] != 1:
                raise ValueError("missing indicator requires exactly one input feature")
            return X.iloc[:, 0].to_numpy()
        array = np.asarray(X, dtype=object)
        if array.ndim == 2 and array.shape[1] == 1:
            return array[:, 0]
        if array.ndim == 1:
            return array
        raise ValueError("missing indicator requires exactly one input feature")
