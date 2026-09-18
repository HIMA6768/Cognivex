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
    MutationFeatureSelection,
    MutationPreprocessingMetadata,
    MutationSelectionMetadata,
    PreprocessingMetadata,
    PreprocessingTask,
    PreprocessingTrack,
    SplitEligibilityCount,
)

from .clinical import FeatureFrameGuard, OriginalMissingIndicator
from .mutations import MutationBurdenTransformer, MutationFrequencySelector
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


def _build_clinical_preprocessor(
    schema: PreprocessingSchema, *, standardize_continuous: bool
) -> Pipeline:
    category_map = schema.category_map
    age_transformer: object = StandardScaler() if standardize_continuous else "passthrough"
    positive_nodes_transformer: object = (
        StandardScaler() if standardize_continuous else "passthrough"
    )
    tumor_size_steps: list[tuple[str, object]] = [
        ("imputer", SimpleImputer(strategy="median"))
    ]
    if standardize_continuous:
        tumor_size_steps.append(("scaler", StandardScaler()))
    columns = ColumnTransformer(
        transformers=[
            ("age", age_transformer, ["age_at_diagnosis"]),
            (
                "tumor_size",
                Pipeline(tumor_size_steps),
                ["tumor_size"],
            ),
            (
                "positive_nodes",
                positive_nodes_transformer,
                ["lymph_nodes_examined_positive"],
            ),
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


def build_clinical_survival_preprocessor(schema: PreprocessingSchema) -> Pipeline:
    """Return a fresh, unfitted, unscaled Track A clinical transformer."""
    return _build_clinical_preprocessor(schema, standardize_continuous=False)


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


def build_clinical_mutation_survival_preprocessor(schema: PreprocessingSchema) -> Pipeline:
    """Return a fresh Track D transformer with fit-local mutation selection."""
    expected = schema.clinical_features + schema.mutation_features
    columns = ColumnTransformer(
        transformers=[
            (
                "clinical",
                _build_clinical_preprocessor(schema, standardize_continuous=True),
                list(schema.clinical_features),
            ),
            (
                "mutations",
                MutationFrequencySelector(schema.mutation_features, min_prevalence=0.05),
                list(schema.mutation_features),
            ),
            (
                "burden",
                Pipeline(
                    [
                        ("log1p", MutationBurdenTransformer(schema.mutation_features)),
                        ("scaler", StandardScaler()),
                    ]
                ),
                list(schema.mutation_features),
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
                    expected_columns=expected,
                    nullable_columns=("tumor_size", "er_status_measured_by_ihc"),
                ),
            ),
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
        PreprocessingTask.CLINICAL_MUTATION_SURVIVAL: (
            schema.clinical_features + schema.mutation_features
        ),
    }[task]
    missing = tuple(name for name in feature_names if name not in prepared.columns)
    if missing:
        raise ValueError(f"prepared data is missing task features: {', '.join(missing)}")
    assert_safe_feature_names(
        feature_names,
        allow_raw_mutation_annotations=task is PreprocessingTask.CLINICAL_MUTATION_SURVIVAL,
    )
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
        PreprocessingTask.CLINICAL_MUTATION_SURVIVAL: PreprocessingTrack.TRACK_D,
    }[task]
    clinical_names = schema.clinical_features if task is not PreprocessingTask.SUBTYPE_CLASSIFICATION else ()
    mrna_names = (
        schema.mrna_features
        if task in {
            PreprocessingTask.CLINICAL_MRNA_SURVIVAL,
            PreprocessingTask.SUBTYPE_CLASSIFICATION,
        }
        else ()
    )
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
        PreprocessingTask.CLINICAL_MUTATION_SURVIVAL: (
            "training-only tumor-size median and ER-IHC most-frequent imputation",
            "schema categories with unknown values ignored",
            "training-only StandardScaler for continuous clinical values and log1p mutation burden",
            "NC does not affect Track D survival eligibility",
            "non-positive duration excluded from survival modeling",
        ),
    }[task]
    imputation, encoding, scaling, nc_policy, zero_policy = policies
    mutation_metadata = None
    standardized_continuous_feature_names: tuple[str, ...] = ()
    unscaled_binary_feature_names: tuple[str, ...] = ()
    mutation_policy = "all mutation annotation fields excluded"
    mutation_source_names: tuple[str, ...] = ()
    if task is PreprocessingTask.CLINICAL_MUTATION_SURVIVAL:
        selector = fitted_preprocessor.named_steps["columns"].named_transformers_["mutations"]
        prevalence = dict(selector.prevalence_by_column_)
        retained = set(selector.retained_columns_)
        selection = MutationSelectionMetadata(
            threshold=float(selector.min_prevalence),
            comparison="greater_than_or_equal",
            fit_row_count=selector.fit_row_count_,
            features=tuple(
                MutationFeatureSelection(
                    raw_column=column,
                    gene=column.removesuffix("_mut"),
                    derived_feature_name=f"{column}_present",
                    prevalence=prevalence[column],
                    retained=column in retained,
                )
                for column in schema.mutation_features
            ),
        )
        mutation_metadata = MutationPreprocessingMetadata(
            representation_policy=(
                "trimmed or numeric zero is absent; finite nonzero or annotation string is present; "
                "missing and malformed values are rejected"
            ),
            source_feature_names=schema.mutation_features,
            selection=selection,
            burden_source_feature_count=len(schema.mutation_features),
            burden_feature_name="mutation_burden_log1p",
            burden_transformation="log1p of binary mutation presence count across all source genes",
        )
        standardized_continuous_feature_names = (
            "age_at_diagnosis",
            "tumor_size",
            "lymph_nodes_examined_positive",
            "mutation_burden_log1p",
        )
        unscaled_binary_feature_names = tuple(
            name for name in final_names if name not in standardized_continuous_feature_names
        )
        mutation_policy = "fit-local >=0.05 binary selector plus all-source-gene log1p burden"
        mutation_source_names = schema.mutation_features
    return PreprocessingMetadata(
        task=task,
        track=track,
        source_dataset=source_dataset,
        source_version=source_version,
        fitted_on_split="train",
        eligible_row_count=eligibility.eligible_count,
        excluded_row_count=eligibility.excluded_count,
        exclusion_counts=eligibility.exclusion_counts,
        raw_feature_count=len(clinical_names) + len(mrna_names) + len(mutation_source_names),
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
        mutation_policy=mutation_policy,
        nc_policy=nc_policy,
        zero_duration_policy=zero_policy,
        forbidden_feature_guard_passed=True,
        split_counts=split_counts,
        mutation_metadata=mutation_metadata,
        standardized_continuous_feature_names=standardized_continuous_feature_names,
        unscaled_binary_feature_names=unscaled_binary_feature_names,
    )
def assert_safe_feature_names(
    feature_names: Iterable[str], *, allow_raw_mutation_annotations: bool = False
) -> None:
    """Fail before model consumption when a target, ID, mutation, or audit field leaks."""
    unsafe: list[str] = []
    for feature_name in feature_names:
        normalized = str(feature_name).split("__")[-1].lower()
        if (
            normalized in _FORBIDDEN_EXACT
            or normalized.endswith("_mut") and not allow_raw_mutation_annotations
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
