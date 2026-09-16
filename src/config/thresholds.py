"""Threshold contracts independent of model implementation."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ThresholdSettings:
    """Application thresholds; model confidence remains unset until AI handoff."""

    model_confidence: float | None = None
    # Provisional development-only image-quality defaults.
    min_image_width: int = 640
    min_image_height: int = 480

