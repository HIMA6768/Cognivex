"""Fixed-order, deterministic classification evaluation for R7."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import hashlib

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)

from src.contracts import ClassificationMetrics, PerClassClassificationMetric


@dataclass(frozen=True, slots=True)
class ProbabilityOutput:
    """Probability columns ordered to the frozen subtype class contract."""

    probabilities: np.ndarray
    class_order: tuple[str, ...]


def _validated_labels(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    class_order: tuple[str, ...],
) -> tuple[np.ndarray, np.ndarray]:
    if not class_order or len(class_order) != len(set(class_order)):
        raise ValueError("class_order must be non-empty and unique")
    true = np.asarray(tuple(y_true), dtype=object)
    pred = np.asarray(tuple(y_pred), dtype=object)
    if true.ndim != 1 or pred.ndim != 1 or len(true) == 0 or len(true) != len(pred):
        raise ValueError("y_true and y_pred must be equally sized non-empty sequences")
    allowed = set(class_order)
    if not set(true).issubset(allowed) or not set(pred).issubset(allowed):
        raise ValueError("classification labels must belong to class_order")
    return true, pred


def evaluate_classification(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    *,
    split: str,
    class_order: tuple[str, ...],
    cohort_fingerprint: str,
) -> ClassificationMetrics:
    """Calculate fixed-order metrics while preserving sklearn balanced accuracy."""
    true, pred = _validated_labels(y_true, y_pred, class_order)
    precision, recall, f1, support = precision_recall_fscore_support(
        true,
        pred,
        labels=class_order,
        zero_division=0,
    )
    per_class = tuple(
        PerClassClassificationMetric(
            label=label,
            precision=float(precision[index]),
            recall=float(recall[index]),
            f1=float(f1[index]),
            support=int(support[index]),
        )
        for index, label in enumerate(class_order)
    )
    matrix = confusion_matrix(true, pred, labels=class_order)
    report = classification_report(
        true,
        pred,
        labels=class_order,
        target_names=class_order,
        output_dict=True,
        zero_division=0,
    )
    return ClassificationMetrics(
        split=split,
        row_count=len(true),
        macro_f1=float(
            f1_score(true, pred, labels=class_order, average="macro", zero_division=0)
        ),
        weighted_f1=float(
            f1_score(true, pred, labels=class_order, average="weighted", zero_division=0)
        ),
        accuracy=float(accuracy_score(true, pred)),
        balanced_accuracy=float(balanced_accuracy_score(true, pred)),
        per_class=per_class,
        confusion_matrix=tuple(tuple(int(value) for value in row) for row in matrix),
        classification_report=report,
        cohort_fingerprint=cohort_fingerprint,
    )


def reorder_and_validate_probabilities(
    probabilities: np.ndarray,
    estimator_classes: Sequence[str],
    class_order: tuple[str, ...],
) -> ProbabilityOutput:
    """Validate probabilities and reorder estimator columns to the frozen class order."""
    classes = tuple(str(value) for value in estimator_classes)
    if len(classes) != len(set(classes)):
        raise ValueError("estimator classes must be unique")
    if set(classes) != set(class_order) or len(classes) != len(class_order):
        raise ValueError("estimator class set must exactly match class_order")
    values = np.asarray(probabilities, dtype=float)
    if values.ndim != 2 or values.shape[1] != len(classes):
        raise ValueError("probability matrix width must match estimator classes")
    if not np.isfinite(values).all():
        raise ValueError("probabilities must be finite")
    ordered = np.ascontiguousarray(values[:, [classes.index(label) for label in class_order]])
    if not np.allclose(ordered.sum(axis=1), 1.0, atol=1e-8, rtol=0):
        raise ValueError("probability rows must sum to one")
    if np.any(ordered < 0) or np.any(ordered > 1):
        raise ValueError("probabilities must be between zero and one")
    return ProbabilityOutput(probabilities=ordered, class_order=class_order)


def prediction_digest(predictions: Sequence[str]) -> str:
    """Digest predictions in their canonical cohort order."""
    return hashlib.sha256(
        "\n".join(str(value) for value in predictions).encode("utf-8")
    ).hexdigest()


def probability_digest(ordered_probabilities: np.ndarray) -> str:
    """Digest canonical little-endian float64 probability bytes.

    Values are quantized to 12 decimal places before byte encoding so harmless
    one-ULP differences from parallel tree-probability reduction cannot change
    the persisted reproducibility digest. This is far below reported metric
    precision and does not alter predictions or stored evaluation metrics.
    """
    values = np.round(np.asarray(ordered_probabilities, dtype=float), decimals=12).astype(
        "<f8",
        copy=False,
    )
    if values.ndim != 2 or not np.isfinite(values).all():
        raise ValueError("ordered probabilities must be a finite two-dimensional matrix")
    return hashlib.sha256(np.ascontiguousarray(values).tobytes(order="C")).hexdigest()
