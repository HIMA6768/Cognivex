"""Stable adapter protocols with no widget or model-runtime dependencies."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.contracts.assessment import ClassificationResult, LocalizationResult


class AssessmentImage(Protocol):
    """Minimal P4-normalized image surface needed by future adapters."""

    digest: str
    width: int
    height: int


@runtime_checkable
class ClassifierAdapter(Protocol):
    """Replaceable classifier contract: mock now, ONNX adapter later."""

    def predict(self, image: AssessmentImage) -> ClassificationResult:
        """Return a P6 classification result for one P4-validated image."""


@runtime_checkable
class LocalizationAdapter(Protocol):
    """Replaceable localizer contract: mock now, ONNX/YOLO adapter later."""

    def localize(self, image: AssessmentImage) -> LocalizationResult:
        """Return a P6 localization result for one P4-validated image."""
