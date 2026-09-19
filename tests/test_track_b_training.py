"""R6 Track B validation-only model-selection and finalization tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from src.contracts import TrackBHyperparameters
from src.data.metabric import MetabricPaths
from src.modeling.survival import CoxFitError
from src.modeling.track_b import PenalizedCoxPHAdapter
from src.training.track_a import prepare_track_a_run
from src.training.track_b import (
    TRACK_B_CANDIDATES,
    finalize_track_b,
    prepare_track_b_run,
    select_track_b_candidate,
)


ROOT = Path(__file__).resolve().parents[1]
R5_ARTIFACT_ROOT = ROOT / "artifacts" / "models" / "track_a" / "r5a-track-a-baseline-v1"


@pytest.fixture(scope="module")
def canonical_run():
    return prepare_track_b_run(MetabricPaths.from_repository_root(ROOT))


def test_canonical_preparation_preserves_event_coding_and_r5_eligibility(canonical_run) -> None:
    track_a = prepare_track_a_run(MetabricPaths.from_repository_root(ROOT))

    assert canonical_run.contract.clinical_features == track_a.schema.clinical_features
    assert canonical_run.train_predictors.shape == (1332, 75)
    assert canonical_run.validation_predictors.shape == (285, 75)
    assert canonical_run.test_predictors.shape == (286, 75)
    assert canonical_run.train_patient_ids == track_a.train_patient_ids
    assert canonical_run.validation_patient_ids == track_a.validation_patient_ids
    assert canonical_run.train_events.sum() == track_a.train_events.sum() == 760
    assert canonical_run.validation_events.sum() == track_a.validation_events.sum() == 168
    assert canonical_run.test_events.sum() == 175
    assert set(np.unique(canonical_run.train_events)) == {0, 1}
    assert set(np.unique(canonical_run.validation_events)) == {0, 1}
    assert set(np.unique(canonical_run.test_events)) == {0, 1}


def test_candidate_grid_covers_ridge_elastic_net_and_lasso() -> None:
    assert TRACK_B_CANDIDATES == (
        TrackBHyperparameters(0.05, 0.0),
        TrackBHyperparameters(0.10, 0.0),
        TrackBHyperparameters(0.05, 0.5),
        TrackBHyperparameters(0.10, 0.5),
        TrackBHyperparameters(0.05, 1.0),
        TrackBHyperparameters(0.10, 1.0),
    )


def test_selection_uses_validation_only_records_failures_and_is_reproducible(canonical_run) -> None:
    target = TrackBHyperparameters(0.05, 0.5)
    failed = TrackBHyperparameters(0.10, 1.0)
    instances: list[FakeCox] = []

    class FakeCox:
        def __init__(self, configuration: TrackBHyperparameters) -> None:
            self.configuration = configuration
            self.feature_names: tuple[str, ...] = ()
            self.predict_row_counts: list[int] = []
            instances.append(self)

        def fit(self, values, durations, events, feature_names) -> None:
            if self.configuration == failed:
                raise CoxFitError("controlled candidate failure")
            self.feature_names = feature_names

        def predict_risk(self, values) -> np.ndarray:
            rows = len(values)
            self.predict_row_counts.append(rows)
            if rows == len(canonical_run.validation_durations):
                durations = canonical_run.validation_durations
                return -durations if self.configuration == target else durations
            if rows == len(canonical_run.train_durations):
                return -canonical_run.train_durations
            if rows == len(canonical_run.test_durations):
                # Deliberately make the selected winner poor on test. Test must not change selection.
                return canonical_run.test_durations
            raise AssertionError(f"unexpected prediction row count: {rows}")

    factory = lambda configuration: FakeCox(configuration)
    first = select_track_b_candidate(canonical_run, model_factory=factory)
    second = select_track_b_candidate(canonical_run, model_factory=factory)

    assert first.selected_configuration == second.selected_configuration == target
    assert len(first.leaderboard) == len(TRACK_B_CANDIDATES)
    failed_row = next(row for row in first.leaderboard if row.configuration == failed)
    assert failed_row.status == "FAILED"
    assert failed_row.validation_c_index is None
    assert "controlled candidate failure" in failed_row.error_message
    assert all(
        len(canonical_run.test_durations) not in instance.predict_row_counts
        for instance in instances
    )
    assert first.test_transformed is False
    assert first.test_scored is False


def test_finalization_scores_only_winner_and_compares_frozen_r5(canonical_run) -> None:
    target = TrackBHyperparameters(0.05, 0.5)
    instances: list[FakeCox] = []

    class FakeCox:
        def __init__(self, configuration: TrackBHyperparameters) -> None:
            self.configuration = configuration
            self.feature_names: tuple[str, ...] = ()
            self.predict_row_counts: list[int] = []
            instances.append(self)

        def fit(self, values, durations, events, feature_names) -> None:
            self.feature_names = feature_names

        def predict_risk(self, values) -> np.ndarray:
            rows = len(values)
            self.predict_row_counts.append(rows)
            if rows == len(canonical_run.validation_durations):
                return (
                    -canonical_run.validation_durations
                    if self.configuration == target
                    else canonical_run.validation_durations
                )
            if rows == len(canonical_run.train_durations):
                return -canonical_run.train_durations
            if rows == len(canonical_run.test_durations):
                return -canonical_run.test_durations
            raise AssertionError(f"unexpected prediction row count: {rows}")

    selection = select_track_b_candidate(
        canonical_run,
        model_factory=lambda configuration: FakeCox(configuration),
    )
    result = finalize_track_b(
        selection,
        canonical_run,
        experiment_id="r6-test-finalization",
        r5_artifact_root=R5_ARTIFACT_ROOT,
    )

    assert result.selected_configuration == target
    assert result.test_metric.split == "test"
    assert result.track_a_validation_metric.c_index == pytest.approx(0.6506960067491564)
    assert result.track_a_validation_metric.cohort_fingerprint == result.validation_metric.cohort_fingerprint
    assert result.track_a_test_metric.cohort_fingerprint == result.test_metric.cohort_fingerprint
    assert result.validation_delta == pytest.approx(
        result.validation_metric.c_index - result.track_a_validation_metric.c_index
    )
    assert result.test_delta == pytest.approx(
        result.test_metric.c_index - result.track_a_test_metric.c_index
    )
    assert result.candidate_test_evaluation_count == 0
    assert result.winner_test_evaluation_count == 1
    winner = next(instance for instance in instances if instance.configuration == target)
    non_winners = [instance for instance in instances if instance.configuration != target]
    assert winner.predict_row_counts.count(286) == 1
    assert all(286 not in instance.predict_row_counts for instance in non_winners)


def test_real_penalized_adapter_uses_requested_configuration() -> None:
    values = np.column_stack((np.linspace(-1, 1, 40), np.tile([0.0, 1.0], 20)))
    durations = np.linspace(1, 40, 40)
    events = np.tile([1, 0], 20)
    adapter = PenalizedCoxPHAdapter(TrackBHyperparameters(0.1, 0.5))

    adapter.fit(values, durations, events, ("continuous", "binary"))
    risks = adapter.predict_risk(values)

    assert risks.shape == (40,)
    assert np.isfinite(risks).all()
    assert adapter.fitter.penalizer == 0.1
    assert adapter.fitter.l1_ratio == 0.5
