"""Deterministic development-only P7 adapters with no inference runtime."""

from __future__ import annotations

from enum import Enum
from hashlib import sha256
from math import floor

from src.config.labels import DamageTypeLabel, SeverityLabel
from src.contracts.assessment import (
    BoundingBox,
    ClassificationResult,
    Detection,
    LabelScore,
    LocalizationResult,
    ModelExecutionMode,
    ModelMetadata,
)

from .interfaces import AssessmentImage


class MockClassifierScenario(str, Enum):
    """Explicit development fixtures; no scenario represents real model behavior."""

    HASHED = "HASHED"
    NORMAL_MINOR_SCRATCH = "NORMAL_MINOR_SCRATCH"
    SEVERE = "SEVERE"
    LOW_SCORE = "LOW_SCORE"
    UNAVAILABLE = "UNAVAILABLE"


class MockLocalizationScenario(str, Enum):
    """Explicit development fixtures for all localization caller states."""

    HASHED = "HASHED"
    ONE = "ONE"
    NONE = "NONE"
    MULTIPLE = "MULTIPLE"
    UNAVAILABLE = "UNAVAILABLE"


def _digest_index(image: AssessmentImage) -> int:
    """Derive a repeatable integer from the stable P4 image digest."""
    return int(sha256(image.digest.encode("utf-8")).hexdigest()[:16], 16)


def _metadata(name: str) -> ModelMetadata:
    """Mark every P7 output as mock while real provenance remains pending."""
    return ModelMetadata(
        name=name,
        version=None,
        experiment_id=None,
        preprocessing_version=None,
        execution_mode=ModelExecutionMode.MOCK,
    )


def _all_scores(
    severity: SeverityLabel,
    damage_type: DamageTypeLabel,
    selected_score: float,
) -> tuple[LabelScore, ...]:
    """Return illustrative score entries for every canonical label without calibration claims."""
    return tuple(
        LabelScore(label, selected_score if label is severity else 0.0)
        for label in SeverityLabel
    ) + tuple(
        LabelScore(label, selected_score if label is damage_type else 0.0)
        for label in DamageTypeLabel
    )


class MockClassifierAdapter:
    """Stable digest-driven mock classifier replaceable by a future ONNX adapter."""

    def __init__(
        self,
        scenario: MockClassifierScenario = MockClassifierScenario.HASHED,
        *,
        mock_inference_enabled: bool = True,
    ) -> None:
        self._scenario = scenario
        self._mock_inference_enabled = mock_inference_enabled

    def predict(self, image: AssessmentImage) -> ClassificationResult:
        """Return deterministic mock labels/scores or a controlled unavailable state."""
        if not self._mock_inference_enabled:
            return ClassificationResult(
                severity=None,
                damage_type=None,
                model=_metadata("mock-classifier"),
                available=False,
                unavailable_reason="MOCK_INFERENCE_DISABLED",
            )
        if self._scenario is MockClassifierScenario.UNAVAILABLE:
            return ClassificationResult(
                severity=None,
                damage_type=None,
                model=_metadata("mock-classifier"),
                available=False,
                unavailable_reason="CLASSIFIER_UNAVAILABLE",
            )

        index = _digest_index(image)
        severity = tuple(SeverityLabel)[index % len(SeverityLabel)]
        damage_type = tuple(DamageTypeLabel)[index % len(DamageTypeLabel)]
        score = 0.78
        if self._scenario is MockClassifierScenario.NORMAL_MINOR_SCRATCH:
            severity, damage_type, score = SeverityLabel.MINOR, DamageTypeLabel.SCRATCH, 0.88
        elif self._scenario is MockClassifierScenario.SEVERE:
            severity, damage_type, score = SeverityLabel.SEVERE, DamageTypeLabel.STRUCTURAL, 0.84
        elif self._scenario is MockClassifierScenario.LOW_SCORE:
            severity, damage_type, score = SeverityLabel.MODERATE, DamageTypeLabel.DENT, 0.25
        return ClassificationResult(
            severity=severity,
            damage_type=damage_type,
            model=_metadata("mock-classifier"),
            severity_score=score,
            damage_type_score=score,
            all_scores=_all_scores(severity, damage_type, score),
        )


def _box(image: AssessmentImage, left: float, top: float, right: float, bottom: float) -> BoundingBox:
    """Turn fixed fractional development regions into valid bounds inside actual dimensions."""
    x_min = max(0, min(image.width - 1, floor(image.width * left)))
    y_min = max(0, min(image.height - 1, floor(image.height * top)))
    x_max = max(x_min + 1, min(image.width, floor(image.width * right)))
    y_max = max(y_min + 1, min(image.height, floor(image.height * bottom)))
    return BoundingBox(x_min=x_min, y_min=y_min, x_max=x_max, y_max=y_max)


class MockLocalizationAdapter:
    """Stable image-relative mock localizer replaceable by a future ONNX/YOLO adapter."""

    def __init__(
        self,
        scenario: MockLocalizationScenario = MockLocalizationScenario.HASHED,
        *,
        localization_enabled: bool = True,
        mock_inference_enabled: bool = True,
    ) -> None:
        self._scenario = scenario
        self._localization_enabled = localization_enabled
        self._mock_inference_enabled = mock_inference_enabled

    def localize(self, image: AssessmentImage) -> LocalizationResult:
        """Return deterministic zero/one/multiple detections or explicit availability states."""
        metadata = _metadata("mock-localizer")
        if not self._mock_inference_enabled:
            return LocalizationResult((), metadata, available=False, unavailable_reason="MOCK_INFERENCE_DISABLED")
        if not self._localization_enabled:
            return LocalizationResult((), metadata, available=False, unavailable_reason="LOCALIZATION_DISABLED")
        if self._scenario is MockLocalizationScenario.UNAVAILABLE:
            return LocalizationResult((), metadata, available=False, unavailable_reason="LOCALIZATION_UNAVAILABLE")

        count = _digest_index(image) % 3
        if self._scenario is MockLocalizationScenario.ONE:
            count = 1
        elif self._scenario is MockLocalizationScenario.NONE:
            count = 0
        elif self._scenario is MockLocalizationScenario.MULTIPLE:
            count = 2
        regions = ((0.18, 0.20, 0.62, 0.66), (0.46, 0.34, 0.86, 0.80))
        labels = tuple(DamageTypeLabel)
        detections = tuple(
            Detection(
                damage_type=labels[(_digest_index(image) + position) % len(labels)],
                bounding_box=_box(image, *regions[position]),
                score=0.74 - position * 0.08,
            )
            for position in range(count)
        )
        return LocalizationResult(detections, metadata)
