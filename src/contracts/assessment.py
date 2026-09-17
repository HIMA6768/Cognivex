"""Stable serializable contracts independent of UI and model runtimes."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from math import isfinite
from typing import Any

from src.config.labels import DamageTypeLabel, SeverityLabel


def _serializable(value: Any) -> Any:
    """Convert nested contract values into JSON-compatible standard Python values."""
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _serializable(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_serializable(item) for item in value]
    if isinstance(value, list):
        return [_serializable(item) for item in value]
    if isinstance(value, dict):
        return {key: _serializable(item) for key, item in value.items()}
    return value


class SerializableContract:
    """Provide stable JSON-compatible dictionaries without framework serializers."""

    def to_dict(self) -> dict[str, Any]:
        return _serializable(self)


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_optional_text(value: str | None, field_name: str) -> None:
    if value is not None:
        _require_text(value, field_name)


class QualityCheckName(str, Enum):
    """Stable P5 measurement identifiers."""

    BLUR = "BLUR"
    DARKNESS = "DARKNESS"
    BRIGHTNESS = "BRIGHTNESS"


class QualityReasonCode(str, Enum):
    """Stable P5 failure codes."""

    IMAGE_TOO_BLURRY = "IMAGE_TOO_BLURRY"
    IMAGE_TOO_DARK = "IMAGE_TOO_DARK"
    IMAGE_TOO_BRIGHT = "IMAGE_TOO_BRIGHT"


@dataclass(frozen=True, slots=True)
class ValidationError(SerializableContract):
    """A stable P4 failure code and UI-safe explanation."""

    code: str
    message: str

    def __post_init__(self) -> None:
        _require_text(self.code, "code")
        _require_text(self.message, "message")


@dataclass(frozen=True, slots=True)
class ValidationResult(SerializableContract):
    """Canonical P4 output, usable without retaining image bytes in a contract."""

    passed: bool
    image_digest: str | None
    width: int | None
    height: int | None
    normalized_mode: str | None
    error: ValidationError | None

    def __post_init__(self) -> None:
        if self.passed:
            if self.error is not None:
                raise ValueError("a passing validation result cannot contain an error")
            _require_text(self.image_digest or "", "image_digest")
            if not isinstance(self.width, int) or self.width <= 0:
                raise ValueError("width must be a positive integer for a passing result")
            if not isinstance(self.height, int) or self.height <= 0:
                raise ValueError("height must be a positive integer for a passing result")
            _require_text(self.normalized_mode or "", "normalized_mode")
        elif self.error is None:
            raise ValueError("a failed validation result must contain an error")


@dataclass(frozen=True, slots=True)
class QualityCheckResult(SerializableContract):
    """One P5 measurement, its effective threshold, and safe remediation copy."""

    name: QualityCheckName
    passed: bool
    measured_value: float
    threshold: float
    code: QualityReasonCode | None
    message: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.name, QualityCheckName):
            raise TypeError("name must be a QualityCheckName")
        if not isfinite(self.measured_value) or not isfinite(self.threshold):
            raise ValueError("quality measurements and thresholds must be finite")
        if self.passed and (self.code is not None or self.message is not None):
            raise ValueError("a passing quality check cannot contain a failure code or message")
        if not self.passed:
            if not isinstance(self.code, QualityReasonCode):
                raise TypeError("a failed quality check must contain a QualityReasonCode")
            _require_text(self.message or "", "message")


@dataclass(frozen=True, slots=True)
class QualityReport(SerializableContract):
    """Canonical P5 outcome; it intentionally carries no routing disposition."""

    passed: bool
    checks: tuple[QualityCheckResult, ...]
    reasons: tuple[QualityReasonCode, ...]
    elapsed_ms: float

    def __post_init__(self) -> None:
        if not isfinite(self.elapsed_ms) or self.elapsed_ms < 0:
            raise ValueError("elapsed_ms must be a non-negative finite value")
        if any(not isinstance(check, QualityCheckResult) for check in self.checks):
            raise TypeError("checks must contain QualityCheckResult values")
        if any(not isinstance(reason, QualityReasonCode) for reason in self.reasons):
            raise TypeError("reasons must contain QualityReasonCode values")
        failed_reasons = tuple(check.code for check in self.checks if check.code is not None)
        if self.reasons != failed_reasons:
            raise ValueError("reasons must preserve failed check-code order")
        if self.passed != all(check.passed for check in self.checks):
            raise ValueError("passed must match the contained check results")


class ModelExecutionMode(str, Enum):
    """Whether a future adapter is an intentional mock or a live model integration."""

    MOCK = "MOCK"
    LIVE = "LIVE"


@dataclass(frozen=True, slots=True)
class ModelMetadata(SerializableContract):
    """Model provenance fields that remain optional until the AI handoff."""

    name: str
    version: str | None
    experiment_id: str | None
    preprocessing_version: str | None
    execution_mode: ModelExecutionMode
    mock: bool | None = None

    def __post_init__(self) -> None:
        _require_text(self.name, "name")
        _require_optional_text(self.version, "version")
        _require_optional_text(self.experiment_id, "experiment_id")
        _require_optional_text(self.preprocessing_version, "preprocessing_version")
        if not isinstance(self.execution_mode, ModelExecutionMode):
            raise TypeError("execution_mode must be a ModelExecutionMode")
        expected_mock = self.execution_mode is ModelExecutionMode.MOCK
        if self.mock is not None and self.mock is not expected_mock:
            raise ValueError("mock must match execution_mode")
        object.__setattr__(self, "mock", expected_mock)


@dataclass(frozen=True, slots=True)
class LabelScore(SerializableContract):
    """An illustrative normalized mock score; never a calibrated probability."""

    label: SeverityLabel | DamageTypeLabel
    score: float

    def __post_init__(self) -> None:
        if not isinstance(self.label, (SeverityLabel, DamageTypeLabel)):
            raise TypeError("label must be a canonical severity or damage-type label")
        if not isfinite(self.score) or not 0 <= self.score <= 1:
            raise ValueError("score must be a finite value between 0 and 1")


@dataclass(frozen=True, slots=True)
class ClassificationResult(SerializableContract):
    """P7 labels and mock display scores without calibrated confidence policy."""

    severity: SeverityLabel | None
    damage_type: DamageTypeLabel | None
    model: ModelMetadata
    severity_score: float | None = None
    damage_type_score: float | None = None
    all_scores: tuple[LabelScore, ...] = ()
    available: bool = True
    unavailable_reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.model, ModelMetadata):
            raise TypeError("model must be ModelMetadata")
        if not isinstance(self.available, bool):
            raise TypeError("available must be a bool")
        if self.available:
            if not isinstance(self.severity, SeverityLabel):
                raise TypeError("severity must be a SeverityLabel when available")
            if not isinstance(self.damage_type, DamageTypeLabel):
                raise TypeError("damage_type must be a DamageTypeLabel when available")
            if self.unavailable_reason is not None:
                raise ValueError("an available classification cannot contain an unavailable reason")
        elif any(
            value is not None for value in (self.severity, self.damage_type, self.severity_score, self.damage_type_score)
        ) or self.all_scores:
            raise ValueError("an unavailable classification cannot contain predictions or scores")
        elif self.unavailable_reason is None:
            raise ValueError("an unavailable classification must contain an unavailable reason")
        _require_optional_text(self.unavailable_reason, "unavailable_reason")
        for score in (self.severity_score, self.damage_type_score):
            if score is not None and (not isfinite(score) or not 0 <= score <= 1):
                raise ValueError("classification scores must be finite values between 0 and 1")
        if any(not isinstance(score, LabelScore) for score in self.all_scores):
            raise TypeError("all_scores must contain LabelScore values")


@dataclass(frozen=True, slots=True)
class BoundingBox(SerializableContract):
    """Absolute image-coordinate detection bounds after P4 orientation normalization."""

    x_min: float
    y_min: float
    x_max: float
    y_max: float

    def __post_init__(self) -> None:
        coordinates = (self.x_min, self.y_min, self.x_max, self.y_max)
        if not all(isfinite(value) and value >= 0 for value in coordinates):
            raise ValueError("bounding-box coordinates must be finite and non-negative")
        if self.x_max <= self.x_min or self.y_max <= self.y_min:
            raise ValueError("bounding-box maximums must exceed minimums")


@dataclass(frozen=True, slots=True)
class Detection(SerializableContract):
    """One future localization finding using a canonical damage-type label."""

    damage_type: DamageTypeLabel
    bounding_box: BoundingBox
    score: float | None

    def __post_init__(self) -> None:
        if not isinstance(self.damage_type, DamageTypeLabel):
            raise TypeError("damage_type must be a DamageTypeLabel")
        if not isinstance(self.bounding_box, BoundingBox):
            raise TypeError("bounding_box must be a BoundingBox")
        if self.score is not None and not isfinite(self.score):
            raise ValueError("score must be finite when supplied")


@dataclass(frozen=True, slots=True)
class LocalizationResult(SerializableContract):
    """Future P7 localization result with provenance but no model-runtime dependency."""

    detections: tuple[Detection, ...]
    model: ModelMetadata
    available: bool = True
    unavailable_reason: str | None = None

    def __post_init__(self) -> None:
        if any(not isinstance(detection, Detection) for detection in self.detections):
            raise TypeError("detections must contain Detection values")
        if not isinstance(self.model, ModelMetadata):
            raise TypeError("model must be ModelMetadata")
        if not isinstance(self.available, bool):
            raise TypeError("available must be a bool")
        if self.available and self.unavailable_reason is not None:
            raise ValueError("an available localization result cannot contain an unavailable reason")
        if not self.available:
            if self.detections:
                raise ValueError("an unavailable localization result cannot contain detections")
            _require_text(self.unavailable_reason or "", "unavailable_reason")


class RoutingStatus(str, Enum):
    """P8 policy output vocabulary; P6 intentionally does not select one."""

    FAST_TRACK_ELIGIBLE = "FAST_TRACK_ELIGIBLE"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    RESUBMIT_IMAGE = "RESUBMIT_IMAGE"


@dataclass(frozen=True, slots=True)
class RoutingReason(SerializableContract):
    """Policy-owned reason details without prematurely defining a P8 reason vocabulary."""

    code: str
    message: str

    def __post_init__(self) -> None:
        _require_text(self.code, "code")
        _require_text(self.message, "message")


@dataclass(frozen=True, slots=True)
class RoutingDecision(SerializableContract):
    """P8 output contract only; this module contains no routing policy."""

    status: RoutingStatus
    reasons: tuple[RoutingReason, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.status, RoutingStatus):
            raise TypeError("status must be a RoutingStatus")
        if not isinstance(self.reasons, tuple):
            raise TypeError("reasons must be an ordered tuple of RoutingReason values")
        if not self.reasons:
            raise ValueError("reasons must contain at least one RoutingReason")
        if not all(isinstance(reason, RoutingReason) for reason in self.reasons):
            raise TypeError("reasons must contain only RoutingReason values")


@dataclass(frozen=True, slots=True)
class AssessmentResult(SerializableContract):
    """Aggregate P9 handoff that also represents partial pre-model pipelines safely."""

    validation: ValidationResult
    quality: QualityReport | None
    classification: ClassificationResult | None
    localization: LocalizationResult | None
    routing: RoutingDecision | None

    def __post_init__(self) -> None:
        if not isinstance(self.validation, ValidationResult):
            raise TypeError("validation must be a ValidationResult")
        if self.quality is not None and not isinstance(self.quality, QualityReport):
            raise TypeError("quality must be a QualityReport or None")
        if self.classification is not None and not isinstance(
            self.classification, ClassificationResult
        ):
            raise TypeError("classification must be a ClassificationResult or None")
        if self.localization is not None and not isinstance(self.localization, LocalizationResult):
            raise TypeError("localization must be a LocalizationResult or None")
        if self.routing is not None and not isinstance(self.routing, RoutingDecision):
            raise TypeError("routing must be a RoutingDecision or None")
