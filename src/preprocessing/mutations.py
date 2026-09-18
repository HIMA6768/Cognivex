"""Shared mutation annotation semantics and sklearn-compatible R4D transformers."""

from __future__ import annotations

from enum import StrEnum
import math

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.utils.validation import check_is_fitted


class MutationAnnotationKind(StrEnum):
    """Structural meaning of one immutable canonical mutation annotation."""

    ABSENT = "absent"
    PRESENT = "present"
    MISSING = "missing"


def classify_mutation_annotation(value: object) -> tuple[MutationAnnotationKind, str | None]:
    """Classify one raw annotation without assigning magnitude to its identity."""
    if bool(pd.isna(value)):
        return MutationAnnotationKind.MISSING, None
    if isinstance(value, (bool, np.bool_)):
        raise ValueError("mutation annotation values must not be boolean")
    text = str(value).strip()
    if not text:
        return MutationAnnotationKind.MISSING, None
    try:
        numeric = float(text)
    except ValueError:
        return MutationAnnotationKind.PRESENT, text
    if not math.isfinite(numeric):
        raise ValueError("mutation annotation values must be finite")
    if numeric == 0:
        return MutationAnnotationKind.ABSENT, None
    return MutationAnnotationKind.PRESENT, text


def _validated_frame(X: object, expected_columns: tuple[str, ...]) -> pd.DataFrame:
    if not isinstance(X, pd.DataFrame):
        raise TypeError("mutation preprocessing input must be a pandas DataFrame")
    missing = tuple(column for column in expected_columns if column not in X.columns)
    unexpected = tuple(column for column in X.columns if column not in expected_columns)
    if missing:
        raise ValueError(f"mutation preprocessing input is missing columns: {', '.join(missing)}")
    if unexpected:
        raise ValueError(f"mutation preprocessing input contains unexpected columns: {', '.join(unexpected)}")
    return X.loc[:, list(expected_columns)]


def _validate_column_contract(mutation_columns: tuple[str, ...]) -> None:
    if (
        not isinstance(mutation_columns, tuple)
        or not mutation_columns
        or len(mutation_columns) != len(set(mutation_columns))
        or not all(isinstance(column, str) and column.endswith("_mut") for column in mutation_columns)
    ):
        raise ValueError("mutation_columns must be a non-empty ordered unique tuple of raw _mut columns")


def _presence_frame(X: object, expected_columns: tuple[str, ...]) -> pd.DataFrame:
    frame = _validated_frame(X, expected_columns)
    output: dict[str, list[float]] = {}
    for column in expected_columns:
        values: list[float] = []
        for value in frame[column]:
            try:
                kind, _ = classify_mutation_annotation(value)
            except ValueError as error:
                raise ValueError(f"invalid mutation annotation in {column}: {error}") from error
            if kind is MutationAnnotationKind.MISSING:
                raise ValueError(f"missing mutation annotation in {column}")
            values.append(1.0 if kind is MutationAnnotationKind.PRESENT else 0.0)
        output[column] = values
    return pd.DataFrame(output, index=frame.index, dtype=float)


class MutationFrequencySelector(TransformerMixin, BaseEstimator):
    """Select binary mutation-presence predictors from fit-local prevalence."""

    def __init__(self, mutation_columns: tuple[str, ...], min_prevalence: float = 0.05) -> None:
        self.mutation_columns = mutation_columns
        self.min_prevalence = min_prevalence

    def fit(self, X: object, y: object = None) -> "MutationFrequencySelector":
        _validate_column_contract(self.mutation_columns)
        if (
            not isinstance(self.min_prevalence, (int, float))
            or isinstance(self.min_prevalence, bool)
            or not math.isfinite(float(self.min_prevalence))
            or not 0 <= float(self.min_prevalence) <= 1
        ):
            raise ValueError("min_prevalence must be a finite fraction from 0 through 1")
        binary = _presence_frame(X, self.mutation_columns)
        if binary.empty:
            raise ValueError("mutation selector requires at least one fit row")
        prevalence = binary.mean(axis=0)
        self.n_features_in_ = len(self.mutation_columns)
        self.feature_names_in_ = np.asarray(self.mutation_columns, dtype=object)
        self.fit_row_count_ = len(binary)
        self.prevalence_by_column_ = tuple(
            (column, float(prevalence[column])) for column in self.mutation_columns
        )
        self.retained_columns_ = tuple(
            column
            for column, value in self.prevalence_by_column_
            if value >= float(self.min_prevalence)
        )
        self.excluded_columns_ = tuple(
            column for column in self.mutation_columns if column not in self.retained_columns_
        )
        self.output_feature_names_ = tuple(f"{column}_present" for column in self.retained_columns_)
        return self

    def transform(self, X: object) -> np.ndarray:
        check_is_fitted(self, "output_feature_names_")
        binary = _presence_frame(X, self.mutation_columns)
        return binary.loc[:, list(self.retained_columns_)].to_numpy(dtype=float)

    def get_feature_names_out(self, input_features: object = None) -> np.ndarray:
        check_is_fitted(self, "output_feature_names_")
        return np.asarray(self.output_feature_names_, dtype=object)


class MutationBurdenTransformer(TransformerMixin, BaseEstimator):
    """Compute log1p mutation burden across every declared source gene."""

    def __init__(self, mutation_columns: tuple[str, ...]) -> None:
        self.mutation_columns = mutation_columns

    def fit(self, X: object, y: object = None) -> "MutationBurdenTransformer":
        _validate_column_contract(self.mutation_columns)
        binary = _presence_frame(X, self.mutation_columns)
        self.n_features_in_ = len(self.mutation_columns)
        self.feature_names_in_ = np.asarray(self.mutation_columns, dtype=object)
        self.fit_row_count_ = len(binary)
        return self

    def transform(self, X: object) -> np.ndarray:
        check_is_fitted(self, "feature_names_in_")
        binary = _presence_frame(X, self.mutation_columns)
        burden = binary.sum(axis=1).to_numpy(dtype=float)
        return np.log1p(burden).reshape(-1, 1)

    def get_feature_names_out(self, input_features: object = None) -> np.ndarray:
        check_is_fitted(self, "feature_names_in_")
        return np.asarray(["mutation_burden_log1p"], dtype=object)
