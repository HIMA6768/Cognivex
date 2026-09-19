"""Explicit, leak-safe R6 Track B preprocessing."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.utils.validation import check_is_fitted

from src.contracts.track_b import TrackBFeatureContract
from src.data.engineer_compatibility import parse_selected_features
from src.data.metabric import MetabricPaths

from .clinical import FeatureFrameGuard
from .mutations import MutationAnnotationKind, classify_mutation_annotation
from .pipelines import assert_safe_feature_names, build_clinical_survival_preprocessor
from .schema import PreprocessingSchema, load_preprocessing_schema


DEFAULT_SELECTED_FEATURES = Path("ai_handoff_data/v1/selected_features.txt")


def load_track_b_feature_contract(
    repository_root: Path,
    *,
    selected_features_path: Path | None = None,
) -> TrackBFeatureContract:
    """Load the explicit selected-feature contract; never discover genomic columns."""
    root = Path(repository_root).resolve()
    schema = load_preprocessing_schema(MetabricPaths.from_repository_root(root))
    selected = parse_selected_features(selected_features_path or root / DEFAULT_SELECTED_FEATURES)
    contract = TrackBFeatureContract(
        clinical_features=schema.clinical_features,
        expression_features=selected.expression_features,
        mutation_features=selected.mutation_features,
    )
    missing_expression = tuple(
        name for name in contract.expression_features if name not in schema.mrna_features
    )
    missing_mutation = tuple(
        name for name in contract.mutation_features if name not in schema.mutation_features
    )
    if missing_expression or missing_mutation:
        missing = ", ".join(missing_expression + missing_mutation)
        raise ValueError(f"selected Track B features are absent from canonical metadata: {missing}")
    return contract


class SelectedMutationPresenceTransformer(TransformerMixin, BaseEstimator):
    """Map selected annotations through the existing R4D semantics without fitting statistics."""

    def __init__(self, mutation_columns: tuple[str, ...]) -> None:
        self.mutation_columns = mutation_columns

    def _matrix(self, X: object) -> np.ndarray:
        if not isinstance(X, pd.DataFrame):
            raise TypeError("selected mutation input must be a pandas DataFrame")
        if (
            not isinstance(self.mutation_columns, tuple)
            or not self.mutation_columns
            or len(self.mutation_columns) != len(set(self.mutation_columns))
            or any(not name.endswith("_mut") for name in self.mutation_columns)
        ):
            raise ValueError("mutation_columns must be an ordered unique tuple of _mut names")
        missing = tuple(name for name in self.mutation_columns if name not in X.columns)
        unexpected = tuple(name for name in X.columns if name not in self.mutation_columns)
        if missing:
            raise ValueError(f"selected mutation input is missing columns: {', '.join(missing)}")
        if unexpected:
            raise ValueError(f"selected mutation input contains unexpected columns: {', '.join(unexpected)}")
        matrix = np.empty((len(X), len(self.mutation_columns)), dtype=float)
        for column_index, column in enumerate(self.mutation_columns):
            for row_index, value in enumerate(X[column]):
                try:
                    kind, _ = classify_mutation_annotation(value)
                except ValueError as error:
                    raise ValueError(f"invalid mutation annotation in {column}: {error}") from error
                if kind is MutationAnnotationKind.MISSING:
                    raise ValueError(f"missing mutation annotation in {column}")
                matrix[row_index, column_index] = (
                    1.0 if kind is MutationAnnotationKind.PRESENT else 0.0
                )
        return matrix

    def fit(self, X: object, y: object = None) -> "SelectedMutationPresenceTransformer":
        self._matrix(X)
        self.n_features_in_ = len(self.mutation_columns)
        self.feature_names_in_ = np.asarray(self.mutation_columns, dtype=object)
        return self

    def transform(self, X: object) -> np.ndarray:
        check_is_fitted(self, "feature_names_in_")
        return self._matrix(X)

    def get_feature_names_out(self, input_features: object = None) -> np.ndarray:
        check_is_fitted(self, "feature_names_in_")
        return np.asarray(
            [f"{name}_present" for name in self.mutation_columns],
            dtype=object,
        )


def build_track_b_preprocessor(
    schema: PreprocessingSchema,
    contract: TrackBFeatureContract,
) -> Pipeline:
    """Return an unfitted 75-input Track B transformer with frozen R5 clinical semantics."""
    if contract.clinical_features != schema.clinical_features:
        raise ValueError("Track B clinical features must exactly match the frozen R5 schema")
    columns = ColumnTransformer(
        transformers=[
            (
                "clinical",
                build_clinical_survival_preprocessor(schema),
                list(contract.clinical_features),
            ),
            ("expression", StandardScaler(), list(contract.expression_features)),
            (
                "mutation",
                SelectedMutationPresenceTransformer(contract.mutation_features),
                list(contract.mutation_features),
            ),
        ],
        remainder="drop",
        sparse_threshold=0,
        verbose_feature_names_out=False,
    )
    return Pipeline(
        [
            (
                "guard",
                FeatureFrameGuard(
                    expected_columns=contract.raw_features,
                    nullable_columns=("tumor_size", "er_status_measured_by_ihc"),
                ),
            ),
            ("columns", columns),
        ]
    )


def track_b_feature_names(preprocessor: Pipeline) -> tuple[str, ...]:
    """Return the validated fitted Track B model-feature order."""
    names = tuple(str(name) for name in preprocessor.get_feature_names_out())
    assert_safe_feature_names(names)
    if len(names) != 80 or len(names) != len(set(names)):
        raise ValueError("Track B must produce exactly 80 unique model features")
    return names

