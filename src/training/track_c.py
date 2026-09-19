"""Validation-only candidate selection for R7 Track C."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
import re
from typing import Any

import pandas as pd

from src.contracts import (
    AnalysisStatus,
    DataQualityStatus,
    TrackCCandidateDefinition,
    TrackCCandidateResult,
    TrackCExperimentResult,
    TrackCFeatureContract,
)
from src.data import TRACK_C_CLASS_ORDER, OrderedTrackCSplit, TrackCOrderedCohorts
from src.data.metabric import MetabricPaths, load_metabric
from src.data.metabric_quality import evaluate_metabric_quality
from src.data.track_c import load_ordered_track_c_cohorts, load_track_c_feature_contract
from src.evaluation.classification import (
    evaluate_classification,
    prediction_digest,
    probability_digest,
    reorder_and_validate_probabilities,
)
from src.modeling.track_c import TRACK_C_CANDIDATES, build_track_c_candidate


@dataclass(frozen=True, slots=True)
class PreparedTrackCSelection:
    """Train and validation data exposed to model selection."""

    contract: TrackCFeatureContract
    train: OrderedTrackCSplit
    validation: OrderedTrackCSplit

    @property
    def splits(self) -> tuple[OrderedTrackCSplit, OrderedTrackCSplit]:
        return self.train, self.validation


@dataclass(frozen=True, slots=True)
class PreparedTrackCTest:
    """Test data kept outside the validation selection interface."""

    split: OrderedTrackCSplit


@dataclass(frozen=True, slots=True)
class PreparedTrackCRun:
    """Canonical R7 data, with test physically separated from selection."""

    selection: PreparedTrackCSelection
    test: PreparedTrackCTest
    prepared_sha256: str
    manifest_sha256: str
    repository_root: Path


@dataclass(frozen=True, slots=True)
class SelectedTrackCModel:
    """Frozen validation winner before any final test access."""

    pipeline: Any
    definition: TrackCCandidateDefinition
    contract: TrackCFeatureContract
    leaderboard: tuple[TrackCCandidateResult, ...]
    validation_metrics: Any
    candidate_test_evaluation_count: int = 0

    def __post_init__(self) -> None:
        if self.candidate_test_evaluation_count != 0:
            raise ValueError("candidate test evaluation count must remain zero")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_track_c_run(paths: MetabricPaths | None = None) -> PreparedTrackCRun:
    """Load canonical Track C cohorts and keep test outside selection."""
    resolved = paths or MetabricPaths.from_repository_root()
    ingestion = load_metabric(resolved)
    if ingestion.validation.status is not AnalysisStatus.DATA_READY:
        raise ValueError("R7 requires R2 DATA_READY")
    quality = evaluate_metabric_quality(resolved, ingestion=ingestion)
    if quality.status is DataQualityStatus.DATA_QUALITY_BLOCKED:
        raise ValueError("R7 requires non-blocked R3 data quality")
    prepared = pd.read_csv(resolved.prepared_csv, low_memory=False)
    manifest_path = resolved.metadata_dir / "manifest.csv"
    manifest = pd.read_csv(manifest_path)
    contract = load_track_c_feature_contract(resolved.repository_root)
    cohorts: TrackCOrderedCohorts = load_ordered_track_c_cohorts(
        prepared,
        manifest,
        contract=contract,
    )
    return PreparedTrackCRun(
        selection=PreparedTrackCSelection(
            contract=contract,
            train=cohorts.train,
            validation=cohorts.validation,
        ),
        test=PreparedTrackCTest(cohorts.test),
        prepared_sha256=_sha256(resolved.prepared_csv),
        manifest_sha256=_sha256(manifest_path),
        repository_root=resolved.repository_root,
    )


def select_validation_winner(
    leaderboard: tuple[TrackCCandidateResult, ...],
) -> TrackCCandidateResult:
    """Select validation Macro-F1 only, with 1e-12 ties kept in declaration order."""
    if not leaderboard:
        raise ValueError("validation leaderboard must not be empty")
    winner = leaderboard[0]
    for candidate in leaderboard[1:]:
        current = candidate.validation_metrics.macro_f1
        best = winner.validation_metrics.macro_f1
        if current > best and not math.isclose(current, best, abs_tol=1e-12, rel_tol=0):
            winner = candidate
    return winner


def select_track_c_candidate(
    selection: PreparedTrackCSelection,
    *,
    candidates: tuple[TrackCCandidateDefinition, ...] = TRACK_C_CANDIDATES,
    pipeline_factory: Callable[[TrackCCandidateDefinition, TrackCFeatureContract], Any] = build_track_c_candidate,
) -> SelectedTrackCModel:
    """Fit candidates on train and select using validation Macro-F1 only."""
    if not isinstance(selection, PreparedTrackCSelection):
        raise TypeError("selection must be PreparedTrackCSelection")
    if not candidates or len(candidates) != len(set(item.key for item in candidates)):
        raise ValueError("candidate registry must be non-empty with unique keys")
    fitted: dict[str, Any] = {}
    results: list[TrackCCandidateResult] = []
    for definition in candidates:
        pipeline = pipeline_factory(definition, selection.contract)
        pipeline.fit(selection.train.predictors, selection.train.targets)
        predictions = pipeline.predict(selection.validation.predictors)
        metrics = evaluate_classification(
            selection.validation.targets,
            predictions,
            split="validation",
            class_order=TRACK_C_CLASS_ORDER,
            cohort_fingerprint=selection.validation.fingerprint,
        )
        result = TrackCCandidateResult(definition=definition, validation_metrics=metrics)
        fitted[definition.key] = pipeline
        results.append(result)
    leaderboard = tuple(results)
    winner = select_validation_winner(leaderboard)
    return SelectedTrackCModel(
        pipeline=fitted[winner.definition.key],
        definition=winner.definition,
        contract=selection.contract,
        leaderboard=leaderboard,
        validation_metrics=winner.validation_metrics,
    )


def _canonical_test_data(test: PreparedTrackCTest) -> tuple[pd.DataFrame, pd.Series]:
    split = test.split
    if split.split != "test":
        raise ValueError("final Track C evaluation requires the test split")
    expected_fingerprint = hashlib.sha256(
        "\n".join(split.patient_ids).encode("utf-8")
    ).hexdigest()
    if split.fingerprint != expected_fingerprint:
        raise ValueError("test cohort fingerprint is inconsistent with canonical patient order")
    if set(split.predictors.index.astype(str)) != set(split.patient_ids):
        raise ValueError("test predictor index does not match canonical patient IDs")
    if set(split.targets.index.astype(str)) != set(split.patient_ids):
        raise ValueError("test target index does not match canonical patient IDs")
    ordered_index = list(split.patient_ids)
    return split.predictors.loc[ordered_index], split.targets.loc[ordered_index]


def finalize_track_c(
    selection: SelectedTrackCModel,
    test: PreparedTrackCTest,
    *,
    experiment_id: str,
) -> TrackCExperimentResult:
    """Evaluate only the frozen validation winner exactly once on canonical test."""
    if not isinstance(experiment_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", experiment_id):
        raise ValueError("experiment_id must be a non-empty path-safe identifier")
    if not isinstance(selection, SelectedTrackCModel):
        raise TypeError("selection must be SelectedTrackCModel")
    if not isinstance(test, PreparedTrackCTest):
        raise TypeError("test must be PreparedTrackCTest")
    predictors, targets = _canonical_test_data(test)
    predictions = tuple(str(value) for value in selection.pipeline.predict(predictors))
    raw_probabilities = selection.pipeline.predict_proba(predictors)
    probability_output = reorder_and_validate_probabilities(
        raw_probabilities,
        selection.pipeline.classes_,
        TRACK_C_CLASS_ORDER,
    )
    metrics = evaluate_classification(
        targets,
        predictions,
        split="test",
        class_order=TRACK_C_CLASS_ORDER,
        cohort_fingerprint=test.split.fingerprint,
    )
    model_feature_names = selection.contract.expression_features + tuple(
        f"{name}_present" for name in selection.contract.mutation_features
    )
    return TrackCExperimentResult(
        schema_version="1.0",
        experiment_id=experiment_id,
        feature_contract=selection.contract,
        model_feature_names=model_feature_names,
        class_order=TRACK_C_CLASS_ORDER,
        selected_definition=selection.definition,
        leaderboard=selection.leaderboard,
        validation_metrics=selection.validation_metrics,
        test_metrics=metrics,
        test_prediction_digest=prediction_digest(predictions),
        test_probability_digest=probability_digest(probability_output.probabilities),
        test_probability_row_count=len(probability_output.probabilities),
        test_probability_normalized=True,
        candidate_test_evaluation_count=selection.candidate_test_evaluation_count,
        winner_test_evaluation_count=1,
    )
