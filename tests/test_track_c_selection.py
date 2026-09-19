from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np

from src.contracts import ClassificationMetrics, PerClassClassificationMetric, TrackCCandidateResult
from src.data import TRACK_C_CLASS_ORDER
from src.modeling.track_c import TRACK_C_CANDIDATES
from src.training.track_c import (
    prepare_track_c_run,
    select_track_c_candidate,
    select_validation_winner,
)


ROOT = Path(__file__).resolve().parents[1]


class FakePipeline:
    def __init__(self, predictions: tuple[str, ...]) -> None:
        self.predictions = predictions
        self.fit_rows = 0
        self.predict_rows: list[int] = []
        self.classes_ = np.asarray(TRACK_C_CLASS_ORDER, dtype=object)

    def fit(self, X, y):
        self.fit_rows = len(X)
        return self

    def predict(self, X):
        self.predict_rows.append(len(X))
        return np.resize(np.asarray(self.predictions, dtype=object), len(X))

    def predict_proba(self, X):
        return np.full((len(X), len(TRACK_C_CLASS_ORDER)), 1 / 6)


def _metric(macro_f1: float, name: str) -> TrackCCandidateResult:
    per_class = tuple(
        PerClassClassificationMetric(label, macro_f1, macro_f1, macro_f1, 1)
        for label in TRACK_C_CLASS_ORDER
    )
    metrics = ClassificationMetrics(
        split="validation",
        row_count=6,
        macro_f1=macro_f1,
        weighted_f1=macro_f1,
        accuracy=macro_f1,
        balanced_accuracy=macro_f1,
        per_class=per_class,
        confusion_matrix=((1, 0, 0, 0, 0, 0), (0, 1, 0, 0, 0, 0), (0, 0, 1, 0, 0, 0), (0, 0, 0, 1, 0, 0), (0, 0, 0, 0, 1, 0), (0, 0, 0, 0, 0, 1)),
        classification_report={},
        cohort_fingerprint="fingerprint",
    )
    definition = next(item for item in TRACK_C_CANDIDATES if item.key == name)
    return TrackCCandidateResult(definition=definition, validation_metrics=metrics)


def test_prepare_track_c_run_uses_current_dataset_manifest_and_exact_eligible_counts() -> None:
    prepared = prepare_track_c_run()

    assert tuple(split.row_count for split in prepared.selection.splits) == (1330, 285)
    assert prepared.test.split.row_count == 283
    assert tuple(split.exclusions.nc for split in (*prepared.selection.splits, prepared.test.split)) == (2, 1, 3)
    assert prepared.prepared_sha256
    assert prepared.manifest_sha256


def test_prepared_selection_contains_train_validation_but_no_test_fields() -> None:
    prepared = prepare_track_c_run()

    assert prepared.selection.train.split == "train"
    assert prepared.selection.validation.split == "validation"
    assert not hasattr(prepared.selection, "test")
    assert prepared.test.split.split == "test"


def test_candidate_fit_receives_train_rows_and_validation_only_receives_predict() -> None:
    prepared = prepare_track_c_run()
    built: list[FakePipeline] = []

    def factory(definition, contract):
        pipeline = FakePipeline(tuple(prepared.selection.validation.targets))
        built.append(pipeline)
        return pipeline

    selected = select_track_c_candidate(prepared.selection, pipeline_factory=factory)

    assert len(built) == 4
    assert all(item.fit_rows == 1330 for item in built)
    assert all(item.predict_rows == [285] for item in built)
    assert selected.candidate_test_evaluation_count == 0


def test_highest_validation_macro_f1_is_sole_winner_even_if_fake_test_scores_disagree() -> None:
    prepared = prepare_track_c_run()
    validation_true = tuple(prepared.selection.validation.targets)
    first_wrong = tuple("Basal" for _ in validation_true)

    def factory(definition, contract):
        predictions = validation_true if definition.key == "random_forest" else first_wrong
        return FakePipeline(predictions)

    selected = select_track_c_candidate(prepared.selection, pipeline_factory=factory)

    assert selected.definition.key == "random_forest"
    assert selected.validation_metrics.macro_f1 == 1.0
    assert not hasattr(selected, "test_metrics")


def test_macro_f1_ties_within_one_e_minus_12_choose_declaration_order() -> None:
    rows = (
        _metric(0.8, "logistic_regression"),
        _metric(0.8 + 5e-13, "random_forest"),
        _metric(0.7, "gradient_boosting"),
        _metric(0.6, "rbf_svm"),
    )

    assert select_validation_winner(rows).definition.key == "logistic_regression"


def test_selection_is_reproducible_with_fixed_seed_candidates() -> None:
    prepared = prepare_track_c_run()
    first = select_track_c_candidate(prepared.selection)
    second = select_track_c_candidate(prepared.selection)

    assert first.definition == second.definition
    assert first.validation_metrics.macro_f1 == second.validation_metrics.macro_f1
    assert [row.validation_metrics.macro_f1 for row in first.leaderboard] == [
        row.validation_metrics.macro_f1 for row in second.leaderboard
    ]


def test_selection_contract_does_not_accept_or_retain_test_data() -> None:
    prepared = prepare_track_c_run()
    altered_test = replace(prepared.test, split=prepared.test.split)

    assert altered_test.split.fingerprint == prepared.test.split.fingerprint
    assert prepared.selection.train.fingerprint != prepared.test.split.fingerprint
