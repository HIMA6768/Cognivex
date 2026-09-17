"""Fresh, unfitted R4 task-specific preprocessing factories."""

from __future__ import annotations

from collections.abc import Iterable

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from .clinical import FeatureFrameGuard, OriginalMissingIndicator
from .schema import PreprocessingSchema


_FORBIDDEN_EXACT = frozenset(
    {
        "patient_id",
        "split",
        "data_source",
        "overall_survival_months",
        "overall_survival",
        "pam50_+_claudin-low_subtype",
        "survival_eligible",
        "subtype_eligible",
        "eligibility_reason",
    }
)


def _one_hot(categories: tuple[str, ...]) -> OneHotEncoder:
    return OneHotEncoder(
        categories=[list(categories)],
        handle_unknown="ignore",
        sparse_output=False,
        dtype=float,
    )


def build_clinical_survival_preprocessor(schema: PreprocessingSchema) -> Pipeline:
    """Return a fresh, unfitted, unscaled Track A clinical transformer."""
    category_map = schema.category_map
    columns = ColumnTransformer(
        transformers=[
            ("age", "passthrough", ["age_at_diagnosis"]),
            (
                "tumor_size",
                Pipeline([("imputer", SimpleImputer(strategy="median"))]),
                ["tumor_size"],
            ),
            ("positive_nodes", "passthrough", ["lymph_nodes_examined_positive"]),
            ("tumor_stage", _one_hot(category_map["tumor_stage"]), ["tumor_stage"]),
            (
                "er_status",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encoder", _one_hot(category_map["er_status_measured_by_ihc"])),
                    ]
                ),
                ["er_status_measured_by_ihc"],
            ),
            ("pr_status", _one_hot(category_map["pr_status"]), ["pr_status"]),
            ("her2_status", _one_hot(category_map["her2_status"]), ["her2_status"]),
            (
                "tumor_size_missing",
                OriginalMissingIndicator("tumor_size", "tumor_size_was_missing"),
                ["tumor_size"],
            ),
            (
                "er_status_missing",
                OriginalMissingIndicator(
                    "er_status_measured_by_ihc",
                    "er_status_measured_by_ihc_was_missing",
                ),
                ["er_status_measured_by_ihc"],
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
                    expected_columns=schema.clinical_features,
                    nullable_columns=("tumor_size", "er_status_measured_by_ihc"),
                ),
            ),
            ("columns", columns),
        ]
    )


def assert_safe_feature_names(feature_names: Iterable[str]) -> None:
    """Fail before model consumption when a target, ID, mutation, or audit field leaks."""
    unsafe: list[str] = []
    for feature_name in feature_names:
        normalized = str(feature_name).split("__")[-1].lower()
        if (
            normalized in _FORBIDDEN_EXACT
            or normalized.endswith("_mut")
            or "eligibility" in normalized
            or normalized.endswith("_eligible")
        ):
            unsafe.append(str(feature_name))
    if unsafe:
        raise ValueError(f"Forbidden predictor feature names: {', '.join(unsafe)}")


def get_transformed_feature_names(preprocessor: Pipeline) -> tuple[str, ...]:
    """Return and validate the fitted transformer's deterministic public feature order."""
    names = tuple(str(name) for name in preprocessor.get_feature_names_out())
    assert_safe_feature_names(names)
    return names
