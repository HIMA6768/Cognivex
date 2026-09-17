"""Pure P5 photographic quality checks for images already accepted by P4."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from statistics import fmean, median
from time import perf_counter

from PIL import Image

from src.contracts.assessment import (
    QualityCheckName,
    QualityCheckResult,
    QualityReasonCode,
    QualityReport,
)

from .upload_flow import ValidatedImage


_MAX_MEASUREMENT_SIDE = 512
_QUALITY_TILE_GRID_SIDE = 4


@dataclass(frozen=True, slots=True)
class QualityThresholds:
    """Provisional deployment-configured P5 limits, not model thresholds."""

    min_laplacian_variance: float
    min_mean_luminance: float
    max_mean_luminance: float
    min_tile_laplacian_variance: float = 40.0
    min_usable_sharp_tile_ratio: float = 0.75
    min_median_luminance: float = 25.0
    dark_pixel_luminance: float = 20.0
    max_dark_pixel_ratio: float = 0.65
    max_median_luminance: float = 230.0
    bright_pixel_luminance: float = 240.0
    max_bright_pixel_ratio: float = 0.65


def _measurement_image(image: ValidatedImage) -> Image.Image:
    """Create deterministic grayscale pixels from P4's normalized preview bytes."""
    with Image.open(BytesIO(image.preview_data)) as preview:
        rgba = preview.convert("RGBA")
        background = Image.new("RGBA", rgba.size, color=(255, 255, 255, 255))
        composited = Image.alpha_composite(background, rgba).convert("L")
    if max(composited.size) <= _MAX_MEASUREMENT_SIDE:
        return composited
    scale = _MAX_MEASUREMENT_SIDE / max(composited.size)
    size = (round(composited.width * scale), round(composited.height * scale))
    return composited.resize(size, Image.Resampling.BILINEAR)


def _laplacian_variance(image: Image.Image) -> float:
    """Return population variance of a four-neighbor discrete grayscale Laplacian."""
    width, height = image.size
    if width < 3 or height < 3:
        return 0.0
    pixels = _pixel_values(image)
    laplacians = [
        4 * pixels[y * width + x]
        - pixels[y * width + x - 1]
        - pixels[y * width + x + 1]
        - pixels[(y - 1) * width + x]
        - pixels[(y + 1) * width + x]
        for y in range(1, height - 1)
        for x in range(1, width - 1)
    ]
    mean = fmean(laplacians)
    return fmean((value - mean) ** 2 for value in laplacians)


def _tile_laplacian_variances(image: Image.Image) -> tuple[float, ...]:
    """Measure sharpness across a fixed grid so small sharp regions cannot dominate a scene."""
    width, height = image.size
    variances: list[float] = []
    for row in range(_QUALITY_TILE_GRID_SIDE):
        top = round(height * row / _QUALITY_TILE_GRID_SIDE)
        bottom = round(height * (row + 1) / _QUALITY_TILE_GRID_SIDE)
        for column in range(_QUALITY_TILE_GRID_SIDE):
            left = round(width * column / _QUALITY_TILE_GRID_SIDE)
            right = round(width * (column + 1) / _QUALITY_TILE_GRID_SIDE)
            if right - left >= 3 and bottom - top >= 3:
                variances.append(_laplacian_variance(image.crop((left, top, right, bottom))))
    return tuple(variances)


def _usable_sharp_tile_ratio(tile_variances: tuple[float, ...], threshold: float) -> float:
    """Return the share of spatial regions whose local sharpness clears the configured floor."""
    if not tile_variances:
        return 0.0
    return sum(variance >= threshold for variance in tile_variances) / len(tile_variances)


def _ratio_below(pixels: list[int], cutoff: float) -> float:
    """Return the share of pixels strictly darker than the configured luminance cutoff."""
    return sum(pixel < cutoff for pixel in pixels) / len(pixels)


def _ratio_above(pixels: list[int], cutoff: float) -> float:
    """Return the share of pixels strictly brighter than the configured luminance cutoff."""
    return sum(pixel > cutoff for pixel in pixels) / len(pixels)


def _pixel_values(image: Image.Image) -> list[int]:
    """Support Pillow 10 while using the non-deprecated flattened API when available."""
    if hasattr(image, "get_flattened_data"):
        return list(image.get_flattened_data())
    return list(image.getdata())


def _result(
    name: QualityCheckName,
    passed: bool,
    measured_value: float,
    threshold: float,
    code: QualityReasonCode | None = None,
    message: str | None = None,
) -> QualityCheckResult:
    """Build a complete result for both success and failure states."""
    return QualityCheckResult(name, passed, measured_value, threshold, code, message)


def evaluate_quality(image: ValidatedImage, thresholds: QualityThresholds) -> QualityReport:
    """Evaluate deterministic P5 quality checks without structural or AI logic."""
    started_at = perf_counter()
    measurement_image = _measurement_image(image)
    pixels = _pixel_values(measurement_image)
    mean_luminance = fmean(pixels)
    median_luminance = float(median(pixels))
    laplacian_variance = _laplacian_variance(measurement_image)
    tile_variances = _tile_laplacian_variances(measurement_image)
    usable_sharp_tile_ratio = _usable_sharp_tile_ratio(
        tile_variances, thresholds.min_tile_laplacian_variance
    )
    dark_pixel_ratio = _ratio_below(pixels, thresholds.dark_pixel_luminance)
    bright_pixel_ratio = _ratio_above(pixels, thresholds.bright_pixel_luminance)

    blur_passed = (
        laplacian_variance >= thresholds.min_laplacian_variance
        and usable_sharp_tile_ratio >= thresholds.min_usable_sharp_tile_ratio
    )
    darkness_passed = (
        mean_luminance >= thresholds.min_mean_luminance
        and median_luminance >= thresholds.min_median_luminance
        and dark_pixel_ratio <= thresholds.max_dark_pixel_ratio
    )
    brightness_passed = (
        mean_luminance <= thresholds.max_mean_luminance
        and median_luminance <= thresholds.max_median_luminance
        and bright_pixel_ratio <= thresholds.max_bright_pixel_ratio
    )
    checks = (
        _result(
            QualityCheckName.BLUR,
            blur_passed,
            usable_sharp_tile_ratio,
            thresholds.min_usable_sharp_tile_ratio,
            None if blur_passed else QualityReasonCode.IMAGE_TOO_BLURRY,
            None
            if blur_passed
            else (
                "The image appears too blurry for a reliable assessment. Please upload a sharper "
                "photo and keep the damaged area in focus."
            ),
        ),
        _result(
            QualityCheckName.DARKNESS,
            darkness_passed,
            median_luminance,
            thresholds.min_median_luminance,
            None if darkness_passed else QualityReasonCode.IMAGE_TOO_DARK,
            None
            if darkness_passed
            else "The image is too dark to assess reliably. Please retake the photo in better lighting.",
        ),
        _result(
            QualityCheckName.BRIGHTNESS,
            brightness_passed,
            median_luminance,
            thresholds.max_median_luminance,
            None if brightness_passed else QualityReasonCode.IMAGE_TOO_BRIGHT,
            None
            if brightness_passed
            else (
                "The image is too bright to assess reliably. Please retake it with less direct "
                "light or reduce overexposure."
            ),
        ),
    )
    reasons = tuple(check.code for check in checks if check.code is not None)
    return QualityReport(
        passed=all(check.passed for check in checks),
        checks=checks,
        reasons=reasons,
        elapsed_ms=(perf_counter() - started_at) * 1_000,
    )
