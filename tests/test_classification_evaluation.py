from __future__ import annotations

import numpy as np
import pytest
from sklearn.metrics import balanced_accuracy_score, f1_score

from src.data import TRACK_C_CLASS_ORDER, ordered_patient_fingerprint
from src.evaluation.classification import (
    evaluate_classification,
    prediction_digest,
    probability_digest,
    reorder_and_validate_probabilities,
)


def _labels() -> tuple[list[str], list[str]]:
    true = ["Basal", "Her2", "LumA", "LumB", "Normal", "claudin-low"] * 2
    pred = ["Basal", "LumA", "LumA", "LumB", "Basal", "claudin-low"] * 2
    return true, pred


def test_classification_metrics_match_sklearn_macro_weighted_accuracy_and_balanced_accuracy() -> None:
    true, pred = _labels()
    metrics = evaluate_classification(
        true,
        pred,
        split="validation",
        class_order=TRACK_C_CLASS_ORDER,
        cohort_fingerprint="abc123",
    )

    assert metrics.macro_f1 == pytest.approx(
        f1_score(true, pred, labels=TRACK_C_CLASS_ORDER, average="macro", zero_division=0)
    )
    assert metrics.weighted_f1 == pytest.approx(
        f1_score(true, pred, labels=TRACK_C_CLASS_ORDER, average="weighted", zero_division=0)
    )
    assert metrics.accuracy == pytest.approx(8 / 12)
    assert metrics.balanced_accuracy == pytest.approx(balanced_accuracy_score(true, pred))


def test_per_class_metrics_and_confusion_matrix_always_use_six_class_order() -> None:
    true, pred = _labels()
    metrics = evaluate_classification(
        true,
        pred,
        split="test",
        class_order=TRACK_C_CLASS_ORDER,
        cohort_fingerprint="fingerprint",
    )

    assert tuple(item.label for item in metrics.per_class) == TRACK_C_CLASS_ORDER
    assert len(metrics.confusion_matrix) == 6
    assert all(len(row) == 6 for row in metrics.confusion_matrix)
    assert tuple(metrics.classification_report)[:6] == TRACK_C_CLASS_ORDER


def test_missing_holdout_class_keeps_zero_support_and_six_by_six_matrix() -> None:
    metrics = evaluate_classification(
        ["Basal", "Her2"],
        ["Basal", "Basal"],
        split="validation",
        class_order=TRACK_C_CLASS_ORDER,
        cohort_fingerprint="fingerprint",
    )

    assert metrics.per_class[-1].support == 0
    assert metrics.per_class[-1].f1 == 0.0
    assert len(metrics.confusion_matrix) == 6


def test_confusion_matrix_sum_equals_evaluated_row_count() -> None:
    true, pred = _labels()
    metrics = evaluate_classification(
        true,
        pred,
        split="test",
        class_order=TRACK_C_CLASS_ORDER,
        cohort_fingerprint="fingerprint",
    )

    assert sum(sum(row) for row in metrics.confusion_matrix) == metrics.row_count == len(true)


def test_probability_columns_reorder_from_estimator_order_to_frozen_order() -> None:
    estimator_classes = tuple(reversed(TRACK_C_CLASS_ORDER))
    raw = np.asarray([[0.05, 0.10, 0.15, 0.20, 0.20, 0.30]], dtype=float)

    output = reorder_and_validate_probabilities(raw, estimator_classes, TRACK_C_CLASS_ORDER)

    assert output.class_order == TRACK_C_CLASS_ORDER
    np.testing.assert_allclose(output.probabilities, raw[:, ::-1])


def test_probability_rows_must_sum_to_one_and_reject_missing_or_duplicate_classes() -> None:
    valid = np.full((2, 6), 1 / 6, dtype=float)

    with pytest.raises(ValueError, match="class set"):
        reorder_and_validate_probabilities(valid[:, :5], TRACK_C_CLASS_ORDER[:5], TRACK_C_CLASS_ORDER)
    with pytest.raises(ValueError, match="unique"):
        reorder_and_validate_probabilities(
            valid,
            (*TRACK_C_CLASS_ORDER[:5], TRACK_C_CLASS_ORDER[0]),
            TRACK_C_CLASS_ORDER,
        )
    with pytest.raises(ValueError, match="sum to one"):
        reorder_and_validate_probabilities(valid * 2, TRACK_C_CLASS_ORDER, TRACK_C_CLASS_ORDER)
    invalid = valid.copy()
    invalid[0, 0] = np.nan
    with pytest.raises(ValueError, match="finite"):
        reorder_and_validate_probabilities(invalid, TRACK_C_CLASS_ORDER, TRACK_C_CLASS_ORDER)


def test_ordered_prediction_probability_and_cohort_digests_are_stable() -> None:
    predictions = ("Basal", "LumA", "Her2")
    probabilities = np.asarray(
        [[0.7, 0.1, 0.1, 0.05, 0.03, 0.02], [0.1, 0.1, 0.7, 0.05, 0.03, 0.02]],
        dtype=float,
    )

    assert prediction_digest(predictions) == prediction_digest(list(predictions))
    assert probability_digest(probabilities) == probability_digest(probabilities.copy())
    assert ordered_patient_fingerprint(("p1", "p2")) == ordered_patient_fingerprint(("p1", "p2"))
    assert prediction_digest(predictions) != prediction_digest(tuple(reversed(predictions)))
    assert probability_digest(probabilities) != probability_digest(probabilities[::-1])


def test_probability_digest_ignores_parallel_reduction_ulp_jitter() -> None:
    probabilities = np.asarray(
        [[0.7, 0.1, 0.1, 0.05, 0.03, 0.02]],
        dtype=float,
    )
    one_ulp = probabilities.copy()
    one_ulp[0, 0] = np.nextafter(one_ulp[0, 0], 1.0)
    meaningful_change = probabilities.copy()
    meaningful_change[0, 0] += 1e-9

    assert probability_digest(one_ulp) == probability_digest(probabilities)
    assert probability_digest(meaningful_change) != probability_digest(probabilities)
