"""R5 Track A orchestration and split-boundary tests."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.contracts import MatrixDiagnostic
from src.data.metabric import MetabricPaths
from src.modeling.survival import CoxFitError
from src.evaluation.survival import diagnose_design_matrix
from src.preprocessing.pipelines import (
    build_clinical_survival_preprocessor,
    get_transformed_feature_names,
)
from src.training.track_a import (
    FittedTrackABundle,
    TrackAFitStopped,
    evaluate_track_a_subset,
    fit_track_a,
    prepare_track_a_run,
)
from tests.r5_helpers import make_track_a_result


def test_canonical_preparation_uses_locked_train_validation_and_holds_out_test() -> None:
    prepared = prepare_track_a_run(MetabricPaths.from_repository_root())

    assert prepared.train_predictors.shape == (1332, 7)
    assert prepared.validation_predictors.shape == (285, 7)
    assert prepared.train_event_count == 760
    assert prepared.train_censored_count == 572
    assert prepared.validation_event_count == 168
    assert prepared.validation_censored_count == 117
    assert prepared.held_out_test_count == 286
    assert not hasattr(prepared, "test_predictors")
    assert tuple(prepared.train_predictors.columns) == prepared.schema.clinical_features


def test_material_cox_failure_preserves_matrix_and_warning_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    prepared = prepare_track_a_run(MetabricPaths.from_repository_root())

    def fail(self, values, durations, events, feature_names):
        raise CoxFitError("Cox PH fitting failed: singular matrix", warnings=("matrix inversion failed",))

    monkeypatch.setattr("src.training.track_a.LifelinesCoxPHAdapter.fit", fail)

    with pytest.raises(TrackAFitStopped, match="singular matrix") as exc_info:
        fit_track_a(prepared, "r5-stop-test")

    assert isinstance(exc_info.value.matrix_diagnostic, MatrixDiagnostic)
    assert exc_info.value.convergence_warnings == ("matrix inversion failed",)


def test_canonical_track_a_reference_encoding_is_full_rank() -> None:
    prepared = prepare_track_a_run(MetabricPaths.from_repository_root())
    preprocessor = build_clinical_survival_preprocessor(prepared.schema)
    values = preprocessor.fit_transform(prepared.train_predictors)
    names = get_transformed_feature_names(preprocessor)

    diagnostic = diagnose_design_matrix(values, names)

    assert len(names) == 12
    assert diagnostic.rank == diagnostic.feature_count == 12
    assert np.isfinite(diagnostic.condition_number)
    assert diagnostic.zero_variance_features == ()
    assert diagnostic.duplicate_column_pairs == ()
    assert diagnostic.linear_dependencies == ()


def test_rank_deficiency_stops_before_cox_fit(monkeypatch: pytest.MonkeyPatch) -> None:
    prepared = prepare_track_a_run(MetabricPaths.from_repository_root())

    class RankDeficientPreprocessor:
        def fit_transform(self, frame: pd.DataFrame) -> np.ndarray:
            base = np.arange(len(frame), dtype=float)
            return np.column_stack((base, base))

        def transform(self, frame: pd.DataFrame) -> np.ndarray:
            base = np.arange(len(frame), dtype=float)
            return np.column_stack((base, base))

        def get_feature_names_out(self) -> np.ndarray:
            return np.asarray(("first", "duplicate"), dtype=object)

    monkeypatch.setattr(
        "src.training.track_a.build_clinical_survival_preprocessor",
        lambda schema: RankDeficientPreprocessor(),
    )

    def must_not_fit(self, values, durations, events, feature_names):
        raise AssertionError("Cox fit must not be called for a rank-deficient matrix")

    monkeypatch.setattr("src.training.track_a.LifelinesCoxPHAdapter.fit", must_not_fit)

    with pytest.raises(TrackAFitStopped, match="full column rank") as exc_info:
        fit_track_a(prepared, "r5a-rank-gate")

    assert exc_info.value.matrix_diagnostic.rank == 1
    assert exc_info.value.matrix_diagnostic.feature_count == 2


def test_common_subset_evaluation_transforms_and_scores_without_refitting() -> None:
    class Preprocessor:
        def transform(self, frame: pd.DataFrame) -> np.ndarray:
            return frame[["age"]].to_numpy(dtype=float)

    class Model:
        def predict_risk(self, values) -> np.ndarray:
            return np.asarray(values, dtype=float).ravel()

    result = make_track_a_result()
    bundle = FittedTrackABundle(Preprocessor(), Model(), result)
    predictors = pd.DataFrame({"age": [3.0, 2.0, 1.0]})

    metric = evaluate_track_a_subset(
        bundle,
        predictors,
        durations=[1.0, 2.0, 3.0],
        events=[1, 1, 1],
        patient_ids=("p1", "p2", "p3"),
        split="future_common_validation",
    )

    assert metric.c_index == 1.0
    assert metric.row_count == 3
    assert len(metric.cohort_fingerprint) == 64
