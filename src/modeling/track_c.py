"""Frozen sklearn candidate factories for R7 Track C."""

from __future__ import annotations

from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.svm import SVC

from src.contracts import TrackCCandidateDefinition, TrackCFeatureContract
from src.preprocessing.track_c import build_track_c_preprocessor


TRACK_C_CANDIDATES = (
    TrackCCandidateDefinition(
        "logistic_regression",
        "Logistic Regression",
        True,
        {"C": 1.0, "class_weight": "balanced", "max_iter": 2000, "random_state": 42},
    ),
    TrackCCandidateDefinition(
        "random_forest",
        "Random Forest",
        False,
        {
            "n_estimators": 200,
            "max_depth": 8,
            "class_weight": "balanced",
            "n_jobs": -1,
            "random_state": 42,
        },
    ),
    TrackCCandidateDefinition(
        "gradient_boosting",
        "Gradient Boosting",
        False,
        {"n_estimators": 150, "max_depth": 4, "learning_rate": 0.1, "random_state": 42},
    ),
    TrackCCandidateDefinition(
        "rbf_svm",
        "RBF SVM",
        True,
        {
            "C": 1.0,
            "kernel": "rbf",
            "probability": True,
            "class_weight": "balanced",
            "random_state": 42,
        },
    ),
)


def build_track_c_candidate(
    definition: TrackCCandidateDefinition,
    contract: TrackCFeatureContract,
) -> Pipeline:
    """Build one fresh approved pipeline with candidate-specific preprocessing."""
    if definition not in TRACK_C_CANDIDATES:
        raise ValueError("Track C candidate definition is not registered")
    factories = {
        "logistic_regression": LogisticRegression,
        "random_forest": RandomForestClassifier,
        "gradient_boosting": GradientBoostingClassifier,
        "rbf_svm": SVC,
    }
    classifier = factories[definition.key](**definition.parameters)
    return Pipeline(
        [
            (
                "preprocessor",
                build_track_c_preprocessor(
                    contract,
                    scale_expression=definition.scale_expression,
                ),
            ),
            ("classifier", classifier),
        ]
    )
