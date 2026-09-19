"""Leak-safe R6 Track B preparation, selection, and final comparison."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import platform
import subprocess
from typing import Any, Callable

import lifelines
import numpy as np
import pandas as pd
import scipy
import sklearn

from src.artifacts.survival import load_trusted_pickle
from src.contracts import (
    AnalysisStatus,
    ConcordanceResult,
    DataQualityStatus,
    RuntimeProvenance,
    SurvivalCohortSummary,
    TrackBCandidateResult,
    TrackBExperimentResult,
    TrackBFeatureContract,
    TrackBHyperparameters,
)
from src.data.metabric import MetabricPaths, load_metabric
from src.data.metabric_quality import evaluate_metabric_quality
from src.evaluation.survival import harrell_c_index
from src.modeling.survival import CoxFitError
from src.modeling.track_b import PenalizedCoxPHAdapter
from src.preprocessing.eligibility import evaluate_clinical_survival_eligibility
from src.preprocessing.schema import PreprocessingSchema, load_preprocessing_schema
from src.preprocessing.track_b import (
    build_track_b_preprocessor,
    load_track_b_feature_contract,
    track_b_feature_names,
)


TRACK_B_CANDIDATES = (
    TrackBHyperparameters(0.05, 0.0),
    TrackBHyperparameters(0.10, 0.0),
    TrackBHyperparameters(0.05, 0.5),
    TrackBHyperparameters(0.10, 0.5),
    TrackBHyperparameters(0.05, 1.0),
    TrackBHyperparameters(0.10, 1.0),
)


@dataclass(frozen=True, slots=True)
class PreparedTrackBRun:
    schema: PreprocessingSchema
    contract: TrackBFeatureContract
    train_predictors: pd.DataFrame
    validation_predictors: pd.DataFrame
    test_predictors: pd.DataFrame
    train_durations: np.ndarray
    validation_durations: np.ndarray
    test_durations: np.ndarray
    train_events: np.ndarray
    validation_events: np.ndarray
    test_events: np.ndarray
    train_patient_ids: tuple[str, ...]
    validation_patient_ids: tuple[str, ...]
    test_patient_ids: tuple[str, ...]
    prepared_sha256: str
    manifest_sha256: str
    repository_root: Path


@dataclass(frozen=True, slots=True)
class SelectedTrackBModel:
    preprocessor: Any
    model: Any
    contract: TrackBFeatureContract
    model_feature_names: tuple[str, ...]
    selected_configuration: TrackBHyperparameters
    leaderboard: tuple[TrackBCandidateResult, ...]
    train_metric: ConcordanceResult
    validation_metric: ConcordanceResult
    test_transformed: bool = False
    test_scored: bool = False


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fingerprint(patient_ids: tuple[str, ...]) -> str:
    return hashlib.sha256("\n".join(patient_ids).encode("utf-8")).hexdigest()


def _git_commit(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _split_series(prepared: pd.DataFrame, manifest: pd.DataFrame) -> pd.Series:
    split_by_patient = manifest.set_index("patient_id")["split"]
    splits = prepared["patient_id"].map(split_by_patient)
    if splits.isna().any() or not splits.isin(("train", "validation", "test")).all():
        raise ValueError("prepared patients must map to one locked split")
    return splits


def prepare_track_b_run(paths: MetabricPaths | None = None) -> PreparedTrackBRun:
    """Load the canonical cohort and apply the exact R5 survival eligibility mask."""
    resolved = paths or MetabricPaths.from_repository_root()
    ingestion = load_metabric(resolved)
    if ingestion.validation.status is not AnalysisStatus.DATA_READY:
        raise ValueError("R6 requires R2 DATA_READY")
    quality = evaluate_metabric_quality(resolved, ingestion=ingestion)
    if quality.status is DataQualityStatus.DATA_QUALITY_BLOCKED:
        raise ValueError("R6 requires non-blocked R3 data quality")
    prepared = pd.read_csv(resolved.prepared_csv, low_memory=False)
    manifest_path = resolved.metadata_dir / "manifest.csv"
    manifest = pd.read_csv(manifest_path)
    schema = load_preprocessing_schema(resolved)
    contract = load_track_b_feature_contract(resolved.repository_root)
    splits = _split_series(prepared, manifest)
    eligibility = evaluate_clinical_survival_eligibility(
        prepared,
        manifest,
        time_column=schema.survival_time_column,
        event_column=schema.survival_event_column,
    )
    eligible = pd.Series(eligibility.mask, index=prepared.index)
    masks = {
        split: eligible & splits.eq(split)
        for split in ("train", "validation", "test")
    }
    predictors = prepared.loc[:, list(contract.raw_features)].copy()

    def frame(split: str) -> pd.DataFrame:
        return predictors.loc[masks[split]].reset_index(drop=True)

    def target(split: str, column: str, dtype) -> np.ndarray:
        return prepared.loc[masks[split], column].to_numpy(dtype=dtype, copy=True)

    def patient_ids(split: str) -> tuple[str, ...]:
        return tuple(prepared.loc[masks[split], "patient_id"].astype(str))

    return PreparedTrackBRun(
        schema=schema,
        contract=contract,
        train_predictors=frame("train"),
        validation_predictors=frame("validation"),
        test_predictors=frame("test"),
        train_durations=target("train", schema.survival_time_column, float),
        validation_durations=target("validation", schema.survival_time_column, float),
        test_durations=target("test", schema.survival_time_column, float),
        train_events=target("train", schema.survival_event_column, int),
        validation_events=target("validation", schema.survival_event_column, int),
        test_events=target("test", schema.survival_event_column, int),
        train_patient_ids=patient_ids("train"),
        validation_patient_ids=patient_ids("validation"),
        test_patient_ids=patient_ids("test"),
        prepared_sha256=_sha256(resolved.prepared_csv),
        manifest_sha256=_sha256(manifest_path),
        repository_root=resolved.repository_root,
    )


def _validate_matrix(values, feature_names: tuple[str, ...]) -> np.ndarray:
    matrix = np.asarray(values, dtype=float)
    if matrix.ndim != 2 or matrix.shape[1] != len(feature_names):
        raise ValueError("Track B matrix does not match model feature order")
    if not np.isfinite(matrix).all():
        raise ValueError("Track B matrix contains non-finite values")
    mutation_indices = [
        index for index, name in enumerate(feature_names) if name.endswith("_mut_present")
    ]
    if len(mutation_indices) != 18:
        raise ValueError("Track B matrix must contain exactly 18 mutation-presence features")
    if not set(np.unique(matrix[:, mutation_indices])).issubset({0.0, 1.0}):
        raise ValueError("Track B mutation-presence matrix must be binary")
    return matrix


def select_track_b_candidate(
    prepared: PreparedTrackBRun,
    *,
    candidates: tuple[TrackBHyperparameters, ...] = TRACK_B_CANDIDATES,
    model_factory: Callable[[TrackBHyperparameters], Any] = PenalizedCoxPHAdapter,
) -> SelectedTrackBModel:
    """Fit preprocessing/candidates on train and select exclusively by validation C-index."""
    if not candidates or len(candidates) != len(set(candidates)):
        raise ValueError("candidate grid must be non-empty and unique")
    preprocessor = build_track_b_preprocessor(prepared.schema, prepared.contract)
    train_values = preprocessor.fit_transform(prepared.train_predictors)
    validation_values = preprocessor.transform(prepared.validation_predictors)
    feature_names = track_b_feature_names(preprocessor)
    train_matrix = _validate_matrix(train_values, feature_names)
    validation_matrix = _validate_matrix(validation_values, feature_names)
    leaderboard: list[TrackBCandidateResult] = []
    fitted: dict[TrackBHyperparameters, Any] = {}
    metrics: dict[TrackBHyperparameters, ConcordanceResult] = {}
    for configuration in candidates:
        model = model_factory(configuration)
        try:
            model.fit(
                train_matrix,
                prepared.train_durations,
                prepared.train_events,
                feature_names,
            )
            metric = harrell_c_index(
                prepared.validation_durations,
                prepared.validation_events,
                model.predict_risk(validation_matrix),
                split="validation",
                cohort_fingerprint=_fingerprint(prepared.validation_patient_ids),
            )
        except CoxFitError as error:
            leaderboard.append(
                TrackBCandidateResult(configuration, "FAILED", None, str(error))
            )
            continue
        fitted[configuration] = model
        metrics[configuration] = metric
        leaderboard.append(
            TrackBCandidateResult(configuration, "CONVERGED", metric.c_index, None)
        )
    successful = [row for row in leaderboard if row.status == "CONVERGED"]
    if not successful:
        raise CoxFitError("all predefined Track B candidates failed")
    winner_row = max(successful, key=lambda row: float(row.validation_c_index))
    winner = fitted[winner_row.configuration]
    train_metric = harrell_c_index(
        prepared.train_durations,
        prepared.train_events,
        winner.predict_risk(train_matrix),
        split="train",
        cohort_fingerprint=_fingerprint(prepared.train_patient_ids),
    )
    return SelectedTrackBModel(
        preprocessor=preprocessor,
        model=winner,
        contract=prepared.contract,
        model_feature_names=feature_names,
        selected_configuration=winner_row.configuration,
        leaderboard=tuple(leaderboard),
        train_metric=train_metric,
        validation_metric=metrics[winner_row.configuration],
    )


def _cohort(split: str, events: np.ndarray, patient_ids: tuple[str, ...]) -> SurvivalCohortSummary:
    event_count = int(np.asarray(events, dtype=int).sum())
    return SurvivalCohortSummary(
        split=split,
        row_count=len(events),
        event_count=event_count,
        censored_count=len(events) - event_count,
        cohort_fingerprint=_fingerprint(patient_ids),
    )


def _load_frozen_track_a_metrics(
    prepared: PreparedTrackBRun,
    artifact_root: Path,
) -> tuple[ConcordanceResult, ConcordanceResult]:
    root = Path(artifact_root)
    metrics = json.loads((root / "metrics.json").read_text(encoding="utf-8"))
    preprocessor = load_trusted_pickle(root / "preprocessor.pkl", trusted=True)
    model = load_trusted_pickle(root / "cox_model.pkl", trusted=True)
    clinical = list(prepared.contract.clinical_features)
    validation_values = preprocessor.transform(prepared.validation_predictors.loc[:, clinical])
    test_values = preprocessor.transform(prepared.test_predictors.loc[:, clinical])
    validation = harrell_c_index(
        prepared.validation_durations,
        prepared.validation_events,
        model.predict_risk(validation_values),
        split="validation",
        cohort_fingerprint=_fingerprint(prepared.validation_patient_ids),
    )
    expected_validation = float(metrics["validation"]["c_index"])
    if not np.isclose(validation.c_index, expected_validation, atol=1e-12, rtol=0):
        raise ValueError("frozen R5 validation metric did not reproduce")
    test = harrell_c_index(
        prepared.test_durations,
        prepared.test_events,
        model.predict_risk(test_values),
        split="test",
        cohort_fingerprint=_fingerprint(prepared.test_patient_ids),
    )
    return validation, test


def finalize_track_b(
    selection: SelectedTrackBModel,
    prepared: PreparedTrackBRun,
    *,
    experiment_id: str,
    r5_artifact_root: Path,
) -> TrackBExperimentResult:
    """Evaluate the frozen winner once on test and compare the frozen R5 model."""
    if not isinstance(experiment_id, str) or not experiment_id.strip():
        raise ValueError("experiment_id must be non-empty")
    test_values = selection.preprocessor.transform(prepared.test_predictors)
    test_matrix = _validate_matrix(test_values, selection.model_feature_names)
    test_metric = harrell_c_index(
        prepared.test_durations,
        prepared.test_events,
        selection.model.predict_risk(test_matrix),
        split="test",
        cohort_fingerprint=_fingerprint(prepared.test_patient_ids),
    )
    track_a_validation, track_a_test = _load_frozen_track_a_metrics(
        prepared, r5_artifact_root
    )
    runtime = RuntimeProvenance(
        python_version=platform.python_version(),
        lifelines_version=lifelines.__version__,
        pandas_version=pd.__version__,
        numpy_version=np.__version__,
        scipy_version=scipy.__version__,
        sklearn_version=sklearn.__version__,
        git_commit=_git_commit(prepared.repository_root),
        prepared_sha256=prepared.prepared_sha256,
        manifest_sha256=prepared.manifest_sha256,
    )
    return TrackBExperimentResult(
        schema_version="1.0",
        experiment_id=experiment_id,
        feature_contract=selection.contract,
        model_feature_names=selection.model_feature_names,
        selected_configuration=selection.selected_configuration,
        leaderboard=selection.leaderboard,
        train_cohort=_cohort("train", prepared.train_events, prepared.train_patient_ids),
        validation_cohort=_cohort(
            "validation", prepared.validation_events, prepared.validation_patient_ids
        ),
        test_cohort=_cohort("test", prepared.test_events, prepared.test_patient_ids),
        train_metric=selection.train_metric,
        validation_metric=selection.validation_metric,
        test_metric=test_metric,
        track_a_validation_metric=track_a_validation,
        track_a_test_metric=track_a_test,
        validation_delta=selection.validation_metric.c_index - track_a_validation.c_index,
        test_delta=test_metric.c_index - track_a_test.c_index,
        candidate_test_evaluation_count=0,
        winner_test_evaluation_count=1,
        runtime=runtime,
    )

