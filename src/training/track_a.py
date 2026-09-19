"""Leak-safe R5 orchestration for the clinical-only Track A Cox baseline."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import platform
import subprocess
from typing import Any

import lifelines
import numpy as np
import pandas as pd
import scipy
import sklearn

from src.contracts import (
    AnalysisStatus,
    CategoricalFeatureComparison,
    CoxModelConfiguration,
    DataQualityStatus,
    MatrixDiagnostic,
    PreprocessingTask,
    RuntimeProvenance,
    SurvivalCohortSummary,
    TrackAExperimentResult,
)
from src.data.metabric import MetabricPaths, load_metabric
from src.data.metabric_quality import evaluate_metabric_quality
from src.evaluation.survival import diagnose_design_matrix, harrell_c_index
from src.modeling.survival import CoxFitError, LifelinesCoxPHAdapter
from src.preprocessing.eligibility import evaluate_clinical_survival_eligibility
from src.preprocessing.pipelines import (
    TRACK_A_REFERENCE_CATEGORIES,
    build_clinical_survival_preprocessor,
    get_transformed_feature_names,
    select_task_features,
)
from src.preprocessing.schema import PreprocessingSchema, load_preprocessing_schema


@dataclass(frozen=True, slots=True)
class PreparedTrackARun:
    schema: PreprocessingSchema
    train_predictors: pd.DataFrame
    validation_predictors: pd.DataFrame
    train_durations: np.ndarray
    train_events: np.ndarray
    validation_durations: np.ndarray
    validation_events: np.ndarray
    train_patient_ids: tuple[str, ...]
    validation_patient_ids: tuple[str, ...]
    held_out_test_count: int
    prepared_sha256: str
    manifest_sha256: str
    repository_root: Path

    @property
    def train_event_count(self) -> int:
        return int(self.train_events.sum())

    @property
    def train_censored_count(self) -> int:
        return len(self.train_events) - self.train_event_count

    @property
    def validation_event_count(self) -> int:
        return int(self.validation_events.sum())

    @property
    def validation_censored_count(self) -> int:
        return len(self.validation_events) - self.validation_event_count


@dataclass(frozen=True, slots=True)
class FittedTrackABundle:
    preprocessor: Any
    model: Any
    result: TrackAExperimentResult


class TrackAFitStopped(RuntimeError):
    """Approved stop condition carrying matrix and convergence evidence."""

    def __init__(
        self,
        message: str,
        *,
        matrix_diagnostic: MatrixDiagnostic,
        convergence_warnings: tuple[str, ...] = (),
    ) -> None:
        super().__init__(message)
        self.matrix_diagnostic = matrix_diagnostic
        self.convergence_warnings = convergence_warnings


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fingerprint(patient_ids: tuple[str, ...]) -> str:
    return hashlib.sha256("\n".join(patient_ids).encode("utf-8")).hexdigest()


def _split_series(prepared: pd.DataFrame, manifest: pd.DataFrame) -> pd.Series:
    split_by_patient = manifest.set_index("patient_id")["split"]
    splits = prepared["patient_id"].map(split_by_patient)
    if splits.isna().any() or not splits.isin(("train", "validation", "test")).all():
        raise ValueError("prepared patients must map to one locked split")
    return splits


def prepare_track_a_run(paths: MetabricPaths | None = None) -> PreparedTrackARun:
    """Prepare train/validation only; retain test solely as an aggregate held-out count."""
    resolved = paths or MetabricPaths.from_repository_root()
    ingestion = load_metabric(resolved)
    if ingestion.validation.status is not AnalysisStatus.DATA_READY:
        raise ValueError("R5 requires R2 DATA_READY")
    quality = evaluate_metabric_quality(resolved, ingestion=ingestion)
    if quality.status is DataQualityStatus.DATA_QUALITY_BLOCKED:
        raise ValueError("R5 requires non-blocked R3 data quality")

    prepared = pd.read_csv(resolved.prepared_csv, low_memory=False)
    manifest_path = resolved.metadata_dir / "manifest.csv"
    manifest = pd.read_csv(manifest_path)
    schema = load_preprocessing_schema(resolved)
    splits = _split_series(prepared, manifest)
    eligibility = evaluate_clinical_survival_eligibility(
        prepared,
        manifest,
        time_column=schema.survival_time_column,
        event_column=schema.survival_event_column,
    )
    eligible = pd.Series(eligibility.mask, index=prepared.index)
    train_mask = eligible & splits.eq("train")
    validation_mask = eligible & splits.eq("validation")
    test_mask = eligible & splits.eq("test")
    predictors = select_task_features(prepared, PreprocessingTask.CLINICAL_SURVIVAL, schema)

    def target(mask: pd.Series, column: str, dtype) -> np.ndarray:
        return prepared.loc[mask, column].to_numpy(dtype=dtype, copy=True)

    return PreparedTrackARun(
        schema=schema,
        train_predictors=predictors.loc[train_mask].reset_index(drop=True),
        validation_predictors=predictors.loc[validation_mask].reset_index(drop=True),
        train_durations=target(train_mask, schema.survival_time_column, float),
        train_events=target(train_mask, schema.survival_event_column, int),
        validation_durations=target(validation_mask, schema.survival_time_column, float),
        validation_events=target(validation_mask, schema.survival_event_column, int),
        train_patient_ids=tuple(prepared.loc[train_mask, "patient_id"].astype(str)),
        validation_patient_ids=tuple(prepared.loc[validation_mask, "patient_id"].astype(str)),
        held_out_test_count=int(test_mask.sum()),
        prepared_sha256=_sha256(resolved.prepared_csv),
        manifest_sha256=_sha256(manifest_path),
        repository_root=resolved.repository_root,
    )


def _git_commit(root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _categorical_comparisons(
    schema: PreprocessingSchema,
    feature_names: tuple[str, ...],
) -> tuple[CategoricalFeatureComparison, ...]:
    comparisons: list[CategoricalFeatureComparison] = []
    for raw_variable, reference_category in TRACK_A_REFERENCE_CATEGORIES:
        for category in schema.category_map[raw_variable]:
            if category == reference_category:
                continue
            derived_feature_name = f"{raw_variable}_{category}"
            if derived_feature_name not in feature_names:
                raise ValueError(
                    f"Track A categorical feature metadata is missing {derived_feature_name}"
                )
            comparisons.append(
                CategoricalFeatureComparison(
                    raw_variable=raw_variable,
                    category=category,
                    reference_category=reference_category,
                    derived_feature_name=derived_feature_name,
                )
            )
    return tuple(comparisons)


def fit_track_a(prepared: PreparedTrackARun, experiment_id: str) -> FittedTrackABundle:
    """Fit the approved train-only baseline and evaluate validation without touching test."""
    if not isinstance(experiment_id, str) or not experiment_id.strip():
        raise ValueError("experiment_id must be a non-empty string")
    preprocessor = build_clinical_survival_preprocessor(prepared.schema)
    train_values = preprocessor.fit_transform(prepared.train_predictors)
    validation_values = preprocessor.transform(prepared.validation_predictors)
    feature_names = get_transformed_feature_names(preprocessor)
    matrix = diagnose_design_matrix(train_values, feature_names)
    if not matrix.all_finite:
        raise TrackAFitStopped("Track A transformed matrix contains non-finite values", matrix_diagnostic=matrix)
    if matrix.rank != matrix.feature_count:
        raise TrackAFitStopped(
            "Track A transformed matrix does not have full column rank",
            matrix_diagnostic=matrix,
        )
    if not np.isfinite(matrix.condition_number):
        raise TrackAFitStopped(
            "Track A transformed matrix has a non-finite condition number",
            matrix_diagnostic=matrix,
        )

    model = LifelinesCoxPHAdapter()
    try:
        model.fit(train_values, prepared.train_durations, prepared.train_events, feature_names)
    except CoxFitError as error:
        raise TrackAFitStopped(
            str(error),
            matrix_diagnostic=matrix,
            convergence_warnings=error.warnings,
        ) from error

    train_fingerprint = _fingerprint(prepared.train_patient_ids)
    validation_fingerprint = _fingerprint(prepared.validation_patient_ids)
    train_metric = harrell_c_index(
        prepared.train_durations,
        prepared.train_events,
        model.predict_risk(train_values),
        split="train",
        cohort_fingerprint=train_fingerprint,
    )
    validation_metric = harrell_c_index(
        prepared.validation_durations,
        prepared.validation_events,
        model.predict_risk(validation_values),
        split="validation",
        cohort_fingerprint=validation_fingerprint,
    )
    configuration = CoxModelConfiguration(
        track="track_a",
        task="clinical_survival",
        model_type="CoxPHFitter",
        baseline_estimation_method="breslow",
        penalizer=0.0,
        l1_ratio=0.0,
        strata=(),
        alpha=0.05,
        duration_column=prepared.schema.survival_time_column,
        event_column=prepared.schema.survival_event_column,
        feature_names=feature_names,
        categorical_comparisons=_categorical_comparisons(prepared.schema, feature_names),
    )
    result = TrackAExperimentResult(
        schema_version="1.0",
        experiment_id=experiment_id,
        configuration=configuration,
        train_cohort=SurvivalCohortSummary(
            "train", len(prepared.train_events), prepared.train_event_count,
            prepared.train_censored_count, train_fingerprint,
        ),
        validation_cohort=SurvivalCohortSummary(
            "validation", len(prepared.validation_events), prepared.validation_event_count,
            prepared.validation_censored_count, validation_fingerprint,
        ),
        held_out_test_count=prepared.held_out_test_count,
        test_transformed=False,
        test_predicted=False,
        test_scored=False,
        matrix_diagnostic=matrix,
        train_metric=train_metric,
        validation_metric=validation_metric,
        coefficients=model.coefficient_estimates(),
        ph_diagnostics=model.evaluate_ph_assumptions(),
        convergence_status="CONVERGED",
        convergence_warnings=model.convergence_warnings,
        runtime=RuntimeProvenance(
            python_version=platform.python_version(),
            lifelines_version=lifelines.__version__,
            pandas_version=pd.__version__,
            numpy_version=np.__version__,
            scipy_version=scipy.__version__,
            sklearn_version=sklearn.__version__,
            git_commit=_git_commit(prepared.repository_root),
            prepared_sha256=prepared.prepared_sha256,
            manifest_sha256=prepared.manifest_sha256,
        ),
    )
    return FittedTrackABundle(preprocessor, model, result)


def evaluate_track_a_subset(
    bundle: FittedTrackABundle,
    raw_predictors: pd.DataFrame,
    durations,
    events,
    patient_ids: tuple[str, ...],
    *,
    split: str,
):
    """Evaluate a supplied future common cohort without refitting either object."""
    if len(raw_predictors) != len(patient_ids):
        raise ValueError("raw predictors and patient IDs must align")
    values = bundle.preprocessor.transform(raw_predictors)
    risks = bundle.model.predict_risk(values)
    return harrell_c_index(
        durations,
        events,
        risks,
        split=split,
        cohort_fingerprint=_fingerprint(patient_ids),
    )
