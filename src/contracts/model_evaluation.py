"""Aggregate-only, checksum-verified model-evaluation contracts for OncoMap."""

from __future__ import annotations

from dataclasses import dataclass
import math

from .analysis import SerializableContract


MIXED_EVIDENCE_INTERPRETATION = (
    "The genomic model performed slightly better on the held-out test cohort, while validation "
    "performance was slightly lower. Overall evidence is mixed, so the project does not claim a "
    "confirmed generalizable improvement from adding genomics."
)


def _finite(value: float, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


@dataclass(frozen=True, slots=True)
class SurvivalMetricView(SerializableContract):
    """Frozen aggregate C-index metrics for one survival model."""

    validation_c_index: float
    test_c_index: float

    def __post_init__(self) -> None:
        _finite(self.validation_c_index, "validation_c_index")
        _finite(self.test_c_index, "test_c_index")


@dataclass(frozen=True, slots=True)
class ClassificationMetricView(SerializableContract):
    """Frozen aggregate held-out metrics for the subtype classifier."""

    test_macro_f1: float
    test_weighted_f1: float
    test_accuracy: float
    test_balanced_accuracy: float

    def __post_init__(self) -> None:
        for name in (
            "test_macro_f1",
            "test_weighted_f1",
            "test_accuracy",
            "test_balanced_accuracy",
        ):
            _finite(getattr(self, name), name)


@dataclass(frozen=True, slots=True)
class ModelEvaluationView(SerializableContract):
    """The complete aggregate-only comparison surface available to the UI."""

    track_a: SurvivalMetricView
    track_b: SurvivalMetricView
    track_c: ClassificationMetricView
    validation_delta: float
    test_delta: float
    interpretation: str = MIXED_EVIDENCE_INTERPRETATION

    def __post_init__(self) -> None:
        if not isinstance(self.track_a, SurvivalMetricView) or not isinstance(self.track_b, SurvivalMetricView):
            raise TypeError("track_a and track_b must be SurvivalMetricView")
        if not isinstance(self.track_c, ClassificationMetricView):
            raise TypeError("track_c must be ClassificationMetricView")
        _finite(self.validation_delta, "validation_delta")
        _finite(self.test_delta, "test_delta")
        if self.interpretation != MIXED_EVIDENCE_INTERPRETATION:
            raise ValueError("model evaluation interpretation is frozen")


@dataclass(frozen=True, slots=True)
class ModelEvaluationError(SerializableContract):
    """Safe aggregate-read failure without source paths or parser details."""

    code: str
    message: str

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code:
            raise ValueError("code must be non-empty")
        if not isinstance(self.message, str) or not self.message:
            raise ValueError("message must be non-empty")


@dataclass(frozen=True, slots=True)
class ModelEvaluationOutcome(SerializableContract):
    """Exactly one aggregate evaluation view or a safe unavailable state."""

    view: ModelEvaluationView | None
    error: ModelEvaluationError | None

    def __post_init__(self) -> None:
        if (self.view is None) == (self.error is None):
            raise ValueError("exactly one of view or error is required")
