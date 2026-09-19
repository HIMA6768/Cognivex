from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import f1_score

from src.contracts import TrackCCandidateResult, TrackCExclusionSummary
from src.data import (
    TRACK_C_CLASS_ORDER,
    OrderedTrackCSplit,
    load_track_c_feature_contract,
    ordered_patient_fingerprint,
)
from src.modeling.track_c import TRACK_C_CANDIDATES
from src.training.track_c import (
    PreparedTrackCTest,
    SelectedTrackCModel,
    finalize_track_c,
)
from src.evaluation.classification import evaluate_classification


ROOT = Path(__file__).resolve().parents[1]


class FinalPipeline:
    def __init__(self, predictions: tuple[str, ...]) -> None:
        self.predictions = predictions
        self.predict_calls = 0
        self.probability_calls = 0
        self.classes_ = np.asarray(tuple(reversed(TRACK_C_CLASS_ORDER)), dtype=object)

    def predict(self, X):
        self.predict_calls += 1
        return np.asarray(self.predictions, dtype=object)

    def predict_proba(self, X):
        self.probability_calls += 1
        probabilities = np.full((len(X), 6), 0.02, dtype=float)
        for row, label in enumerate(self.predictions):
            probabilities[row, tuple(self.classes_).index(label)] = 0.90
        return probabilities


def _fixture():
    contract = load_track_c_feature_contract(ROOT)
    ids = ("p1", "p2", "p3", "p4", "p5", "p6")
    targets = pd.Series(TRACK_C_CLASS_ORDER, index=pd.Index(ids, name="patient_id"))
    predictors = pd.DataFrame(
        np.zeros((6, 68)),
        index=targets.index,
        columns=contract.raw_features,
    )
    split = OrderedTrackCSplit(
        split="test",
        patient_ids=ids,
        predictors=predictors,
        targets=targets,
        exclusions=TrackCExclusionSummary("test", 6, 6, 0, 0, 0),
        fingerprint=ordered_patient_fingerprint(ids),
    )
    pipeline = FinalPipeline(TRACK_C_CLASS_ORDER)
    validation = evaluate_classification(
        TRACK_C_CLASS_ORDER,
        TRACK_C_CLASS_ORDER,
        split="validation",
        class_order=TRACK_C_CLASS_ORDER,
        cohort_fingerprint="validation-fingerprint",
    )
    definition = TRACK_C_CANDIDATES[0]
    candidate = TrackCCandidateResult(definition, validation)
    selected = SelectedTrackCModel(
        pipeline=pipeline,
        definition=definition,
        contract=contract,
        leaderboard=(candidate,),
        validation_metrics=validation,
    )
    return selected, PreparedTrackCTest(split), pipeline


def test_finalize_calls_test_predict_and_predict_proba_exactly_once_on_winner() -> None:
    selected, test, pipeline = _fixture()

    result = finalize_track_c(selected, test, experiment_id="r7-test")

    assert pipeline.predict_calls == 1
    assert pipeline.probability_calls == 1
    assert result.candidate_test_evaluation_count == 0
    assert result.winner_test_evaluation_count == 1


def test_final_metrics_confusion_and_classification_report_recompute() -> None:
    selected, test, _ = _fixture()

    result = finalize_track_c(selected, test, experiment_id="r7-test")

    assert result.test_metrics.macro_f1 == pytest.approx(
        f1_score(TRACK_C_CLASS_ORDER, TRACK_C_CLASS_ORDER, labels=TRACK_C_CLASS_ORDER, average="macro")
    )
    assert result.test_metrics.classification_report["accuracy"] == 1.0
    assert len(result.test_metrics.confusion_matrix) == 6
    assert sum(sum(row) for row in result.test_metrics.confusion_matrix) == 6


def test_probability_rows_reorder_to_frozen_class_order_and_sum_to_one() -> None:
    selected, test, _ = _fixture()

    result = finalize_track_c(selected, test, experiment_id="r7-test")

    assert result.class_order == TRACK_C_CLASS_ORDER
    assert result.test_prediction_digest
    assert result.test_probability_digest
    assert result.test_probability_row_count == 6
    assert result.test_probability_normalized is True


def test_prediction_probability_and_cohort_digests_use_canonical_test_order() -> None:
    selected, test, _ = _fixture()
    first = finalize_track_c(selected, test, experiment_id="r7-test")
    shuffled_split = replace(
        test.split,
        predictors=test.split.predictors.sample(frac=1, random_state=11),
        targets=test.split.targets.sample(frac=1, random_state=12),
    )
    selected_again, _, _ = _fixture()

    second = finalize_track_c(
        selected_again,
        PreparedTrackCTest(shuffled_split),
        experiment_id="r7-test",
    )

    assert second.test_prediction_digest == first.test_prediction_digest
    assert second.test_probability_digest == first.test_probability_digest
    assert second.test_metrics.cohort_fingerprint == first.test_metrics.cohort_fingerprint


def test_finalization_rejects_unsafe_id_and_inconsistent_cohort_fingerprint() -> None:
    selected, test, _ = _fixture()
    with pytest.raises(ValueError, match="safe"):
        finalize_track_c(selected, test, experiment_id="../unsafe")
    invalid = replace(test.split, fingerprint="incorrect")
    with pytest.raises(ValueError, match="fingerprint"):
        finalize_track_c(selected, PreparedTrackCTest(invalid), experiment_id="r7-test")
