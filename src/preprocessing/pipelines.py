"""Fresh, unfitted R4 task-specific preprocessing factories."""

from __future__ import annotations

from collections.abc import Iterable

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

import pandas as pd

from src.contracts import (
    EligibilityResult,
    PreprocessingMetadata,
    PreprocessingTask,
    PreprocessingTrack,
    SplitEligibilityCount,
)

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


def build_clinical_mrna_survival_preprocessor(schema: PreprocessingSchema) -> Pipeline:
    """Return a fresh Track B transformer with train-fitted mRNA scaling."""
    expected = schema.clinical_features + schema.mrna_features
    columns = ColumnTransformer(
        transformers=[
            ("clinical", build_clinical_survival_preprocessor(schema), list(schema.clinical_features)),
            ("mrna", StandardScaler(), list(schema.mrna_features)),
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
                    expected_columns=expected,
                    nullable_columns=("tumor_size", "er_status_measured_by_ihc"),
                ),
            ),
            ("columns", columns),
        ]
    )


def build_subtype_preprocessor(schema: PreprocessingSchema) -> Pipeline:
    """Return a fresh Track C identity transformer for canonical mRNA Z-scores."""
    columns = ColumnTransformer(
        transformers=[("mrna", "passthrough", list(schema.mrna_features))],
        remainder="drop",
        sparse_threshold=0,
        verbose_feature_names_out=False,
    )
    return Pipeline(
        [
            ("guard", FeatureFrameGuard(expected_columns=schema.mrna_features)),
            ("columns", columns),
        ]
    )


def select_task_features(
    prepared: pd.DataFrame,
    task: PreprocessingTask,
    schema: PreprocessingSchema,
) -> pd.DataFrame:
    """Build an ordered predictor-only frame from the full prepared dataset."""
    if not isinstance(task, PreprocessingTask):
        raise TypeError("task must be a PreprocessingTask")
    feature_names = {
        PreprocessingTask.CLINICAL_SURVIVAL: schema.clinical_features,
        PreprocessingTask.CLINICAL_MRNA_SURVIVAL: schema.clinical_features + schema.mrna_features,
        PreprocessingTask.SUBTYPE_CLASSIFICATION: schema.mrna_features,
    }[task]
    missing = tuple(name for name in feature_names if name not in prepared.columns)
    if missing:
        raise ValueError(f"prepared data is missing task features: {', '.join(missing)}")
    assert_safe_feature_names(feature_names)
    return prepared.loc[:, list(feature_names)].copy()


def build_preprocessing_metadata(
    *,
    task: PreprocessingTask,
    schema: PreprocessingSchema,
    eligibility: EligibilityResult,
    fitted_preprocessor: Pipeline,
    split_counts: tuple[SplitEligibilityCount, ...],
    source_dataset: str,
    source_version: str,
) -> PreprocessingMetadata:
    """Explain one fitted train-only preprocessor without exposing row records."""
    track = {
        PreprocessingTask.CLINICAL_SURVIVAL: PreprocessingTrack.TRACK_A,
        PreprocessingTask.CLINICAL_MRNA_SURVIVAL: PreprocessingTrack.TRACK_B,
        PreprocessingTask.SUBTYPE_CLASSIFICATION: PreprocessingTrack.TRACK_C,
    }[task]
    clinical_names = schema.clinical_features if task is not PreprocessingTask.SUBTYPE_CLASSIFICATION else ()
    mrna_names = schema.mrna_features if task is not PreprocessingTask.CLINICAL_SURVIVAL else ()
    final_names = get_transformed_feature_names(fitted_preprocessor)
    policies = {
        PreprocessingTask.CLINICAL_SURVIVAL: (
            "training-only tumor-size median and ER-IHC most-frequent imputation",
            "schema categories with unknown values ignored",
            "no numeric scaling",
            "NC does not affect survival eligibility",
            "non-positive duration excluded from survival modeling",
        ),
        PreprocessingTask.CLINICAL_MRNA_SURVIVAL: (
            "training-only tumor-size median and ER-IHC most-frequent imputation",
            "schema categories with unknown values ignored",
            "training-only StandardScaler for 489 ordered mRNA features",
            "NC does not affect survival eligibility",
            "non-positive duration excluded from survival modeling",
        ),
        PreprocessingTask.SUBTYPE_CLASSIFICATION: (
            "no predictor imputation",
            "no categorical predictor encoding",
            "canonical METABRIC expression Z-scores retained without additional R4 scaling",
            "NC excluded from supervised subtype classification",
            "survival duration does not affect subtype eligibility",
        ),
    }[task]
    imputation, encoding, scaling, nc_policy, zero_policy = policies
    return PreprocessingMetadata(
        task=task,
        track=track,
        source_dataset=source_dataset,
        source_version=source_version,
        fitted_on_split="train",
        eligible_row_count=eligibility.eligible_count,
        excluded_row_count=eligibility.excluded_count,
        exclusion_counts=eligibility.exclusion_counts,
        raw_feature_count=len(clinical_names) + len(mrna_names),
        transformed_feature_count=len(final_names),
        clinical_feature_names=clinical_names,
        mrna_feature_names=mrna_names,
        final_feature_names=final_names,
        imputation_strategy=imputation,
        missing_indicator_strategy=(
            "original pre-imputation nullness for tumor_size and er_status_measured_by_ihc"
            if clinical_names
            else "no missingness indicators"
        ),
        categorical_encoding_strategy=encoding,
        scaling_strategy=scaling,
        mutation_policy="all mutation annotation fields excluded; Track D deferred",
        nc_policy=nc_policy,
        zero_duration_policy=zero_policy,
        forbidden_feature_guard_passed=True,
        split_counts=split_counts,
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
