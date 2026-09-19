"""Framework-independent R7 Track C feature contracts."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from .analysis import SerializableContract


def _ordered_names(values: tuple[str, ...], field: str) -> None:
    if not isinstance(values, tuple) or not values:
        raise ValueError(f"{field} must be a non-empty ordered tuple")
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError(f"{field} must contain non-empty strings")
    if len(values) != len(set(values)):
        raise ValueError(f"{field} must contain unique names")


@dataclass(frozen=True, slots=True)
class TrackCFeatureContract(SerializableContract):
    """Exact ordered genomic-only predictor contract for R7 Track C."""

    expression_features: tuple[str, ...]
    mutation_features: tuple[str, ...]

    def __post_init__(self) -> None:
        _ordered_names(self.expression_features, "expression_features")
        _ordered_names(self.mutation_features, "mutation_features")
        if len(self.expression_features) != 50:
            raise ValueError("Track C requires exactly 50 expression features")
        if len(self.mutation_features) != 18:
            raise ValueError("Track C requires exactly 18 mutation features")
        if any(name.endswith("_mut") for name in self.expression_features):
            raise ValueError("expression features must not use the mutation suffix")
        if any(not name.endswith("_mut") for name in self.mutation_features):
            raise ValueError("mutation features must use the _mut suffix")
        if len(set(self.raw_features)) != 68:
            raise ValueError("Track C raw feature groups must be disjoint")

    @property
    def raw_features(self) -> tuple[str, ...]:
        return self.expression_features + self.mutation_features


@dataclass(frozen=True, slots=True)
class TrackCExclusionSummary(SerializableContract):
    """Aggregate-only Track C target eligibility for one locked split."""

    split: str
    source_rows: int
    eligible_rows: int
    nc: int
    missing: int
    unsupported: int

    def __post_init__(self) -> None:
        if self.split not in {"train", "validation", "test"}:
            raise ValueError("split must be train, validation, or test")
        values = (self.source_rows, self.eligible_rows, self.nc, self.missing, self.unsupported)
        if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in values):
            raise ValueError("Track C exclusion counts must be non-negative integers")
        if self.eligible_rows + self.nc + self.missing + self.unsupported != self.source_rows:
            raise ValueError("Track C exclusion counts must reconcile to source_rows")


@dataclass(frozen=True, slots=True)
class PerClassClassificationMetric(SerializableContract):
    """One fixed-order subtype classification metric row."""

    label: str
    precision: float
    recall: float
    f1: float
    support: int

    def __post_init__(self) -> None:
        if not isinstance(self.label, str) or not self.label:
            raise ValueError("label must be non-empty")
        if any(
            not math.isfinite(value) or not 0 <= value <= 1
            for value in (self.precision, self.recall, self.f1)
        ):
            raise ValueError("classification rates must be finite values between zero and one")
        if not isinstance(self.support, int) or isinstance(self.support, bool) or self.support < 0:
            raise ValueError("support must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class ClassificationMetrics(SerializableContract):
    """Fixed-order aggregate and per-class metrics for one split."""

    split: str
    row_count: int
    macro_f1: float
    weighted_f1: float
    accuracy: float
    balanced_accuracy: float
    per_class: tuple[PerClassClassificationMetric, ...]
    confusion_matrix: tuple[tuple[int, ...], ...]
    classification_report: dict[str, Any]
    cohort_fingerprint: str

    def __post_init__(self) -> None:
        if self.split not in {"train", "validation", "test"}:
            raise ValueError("split must be train, validation, or test")
        if not isinstance(self.row_count, int) or isinstance(self.row_count, bool) or self.row_count <= 0:
            raise ValueError("row_count must be a positive integer")
        for value in (self.macro_f1, self.weighted_f1, self.accuracy, self.balanced_accuracy):
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError("aggregate classification metrics must be between zero and one")
        if not self.per_class or any(
            not isinstance(item, PerClassClassificationMetric) for item in self.per_class
        ):
            raise TypeError("per_class must contain classification metric rows")
        size = len(self.per_class)
        if len(self.confusion_matrix) != size or any(
            len(row) != size for row in self.confusion_matrix
        ):
            raise ValueError("confusion_matrix dimensions must match per_class")
        if sum(sum(row) for row in self.confusion_matrix) != self.row_count:
            raise ValueError("confusion_matrix must sum to row_count")
        if not isinstance(self.cohort_fingerprint, str) or not self.cohort_fingerprint:
            raise ValueError("cohort_fingerprint must be non-empty")


@dataclass(frozen=True, slots=True)
class TrackCCandidateDefinition(SerializableContract):
    """One frozen R7 classifier family and preprocessing choice."""

    key: str
    display_name: str
    scale_expression: bool
    parameters: dict[str, Any]

    def __post_init__(self) -> None:
        if not isinstance(self.key, str) or not self.key:
            raise ValueError("candidate key must be non-empty")
        if not isinstance(self.display_name, str) or not self.display_name:
            raise ValueError("candidate display_name must be non-empty")
        if not isinstance(self.scale_expression, bool):
            raise TypeError("scale_expression must be boolean")
        if not isinstance(self.parameters, dict) or not self.parameters:
            raise ValueError("candidate parameters must be a non-empty dictionary")


@dataclass(frozen=True, slots=True)
class TrackCCandidateResult(SerializableContract):
    """Validation-only result for one frozen Track C candidate."""

    definition: TrackCCandidateDefinition
    validation_metrics: ClassificationMetrics

    def __post_init__(self) -> None:
        if not isinstance(self.definition, TrackCCandidateDefinition):
            raise TypeError("definition must be TrackCCandidateDefinition")
        if not isinstance(self.validation_metrics, ClassificationMetrics):
            raise TypeError("validation_metrics must be ClassificationMetrics")
        if self.validation_metrics.split != "validation":
            raise ValueError("candidate results must contain validation metrics only")
