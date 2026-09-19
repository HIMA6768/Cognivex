"""Exact R7 Track C preprocessing with train-only expression scaling."""

from __future__ import annotations

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.contracts import TrackCFeatureContract

from .clinical import FeatureFrameGuard
from .pipelines import assert_safe_feature_names
from .track_b import SelectedMutationPresenceTransformer


def build_track_c_preprocessor(
    contract: TrackCFeatureContract,
    *,
    scale_expression: bool,
) -> Pipeline:
    """Return an unfitted exact-column Track C transformer.

    Logistic-regression and RBF-SVM candidates request train-fitted expression
    scaling. Tree candidates pass expression values through unchanged. Mutation
    annotations always use the existing R4D-backed binary transformer and are
    never scaled.
    """
    if not isinstance(contract, TrackCFeatureContract):
        raise TypeError("contract must be TrackCFeatureContract")
    if not isinstance(scale_expression, bool):
        raise TypeError("scale_expression must be boolean")
    expression_transformer = StandardScaler() if scale_expression else "passthrough"
    columns = ColumnTransformer(
        transformers=[
            ("expression", expression_transformer, list(contract.expression_features)),
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
            ("guard", FeatureFrameGuard(expected_columns=contract.raw_features)),
            ("columns", columns),
        ]
    )


def track_c_feature_names(preprocessor: Pipeline) -> tuple[str, ...]:
    """Return the fitted 68-column Track C model feature order."""
    names = tuple(str(name) for name in preprocessor.get_feature_names_out())
    assert_safe_feature_names(names)
    if len(names) != 68 or len(names) != len(set(names)):
        raise ValueError("Track C must produce exactly 68 unique model features")
    if len([name for name in names if name.endswith("_mut_present")]) != 18:
        raise ValueError("Track C must produce exactly 18 mutation-presence features")
    return names
