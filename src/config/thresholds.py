"""Threshold contracts independent of model implementation."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ThresholdSettings:
    """Model-independent confidence and structural image limits."""

    model_confidence: float | None = None
    # Minimum structural image dimensions for preview validation.
    min_image_width: int = 640
    min_image_height: int = 480
    # Operational structural bounds, not quality or AI thresholds.
    max_image_width: int = 8192
    max_image_height: int = 8192
    max_image_pixels: int = 40_000_000
    # Provisional P5 engineering defaults; not validated on vehicle-photo datasets.
    min_laplacian_variance: float = 80.0
    min_mean_luminance: float = 25.0
    max_mean_luminance: float = 230.0
    min_tile_laplacian_variance: float = 40.0
    min_usable_sharp_tile_ratio: float = 0.75
    min_median_luminance: float = 25.0
    dark_pixel_luminance: float = 20.0
    max_dark_pixel_ratio: float = 0.65
    max_median_luminance: float = 230.0
    bright_pixel_luminance: float = 240.0
    max_bright_pixel_ratio: float = 0.65
