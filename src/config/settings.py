"""Environment-backed application settings."""

from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
import os

from .inference import InferenceSettings
from .thresholds import ThresholdSettings
from .uploads import UploadSettings


class ConfigurationError(ValueError):
    """Raised when an application environment value is invalid."""


def _optional_value(environ: Mapping[str, str], variable: str) -> str | None:
    value = environ.get(variable)
    return value.strip() if value and value.strip() else None


def _parse_bool(environ: Mapping[str, str], variable: str, default: bool) -> bool:
    value = _optional_value(environ, variable)
    if value is None:
        return default
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    raise ConfigurationError(f"{variable} must be true or false")


def _parse_optional_confidence(environ: Mapping[str, str]) -> float | None:
    variable = "COGNIVEX_MODEL_CONFIDENCE"
    value = _optional_value(environ, variable)
    if value is None:
        return None
    try:
        confidence = float(value)
    except ValueError as error:
        raise ConfigurationError(f"{variable} must be a number") from error
    if not isfinite(confidence) or not 0 <= confidence <= 1:
        raise ConfigurationError(f"{variable} must be between 0 and 1")
    return confidence


def _parse_positive_int(environ: Mapping[str, str], variable: str, default: int) -> int:
    value = _optional_value(environ, variable)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError as error:
        raise ConfigurationError(f"{variable} must be a whole number") from error
    if parsed <= 0:
        raise ConfigurationError(f"{variable} must be greater than zero")
    return parsed


def _parse_positive_float(environ: Mapping[str, str], variable: str, default: float) -> float:
    value = _optional_value(environ, variable)
    if value is None:
        return default
    try:
        parsed = float(value)
    except ValueError as error:
        raise ConfigurationError(f"{variable} must be a number") from error
    if not isfinite(parsed) or parsed <= 0:
        raise ConfigurationError(f"{variable} must be greater than zero")
    return parsed


def _parse_luminance(environ: Mapping[str, str], variable: str, default: float) -> float:
    value = _optional_value(environ, variable)
    if value is None:
        return default
    try:
        parsed = float(value)
    except ValueError as error:
        raise ConfigurationError(f"{variable} must be a number") from error
    if not isfinite(parsed) or not 0 <= parsed <= 255:
        raise ConfigurationError(f"{variable} must be between 0 and 255")
    return parsed


def _parse_ratio(environ: Mapping[str, str], variable: str, default: float) -> float:
    value = _optional_value(environ, variable)
    if value is None:
        return default
    try:
        parsed = float(value)
    except ValueError as error:
        raise ConfigurationError(f"{variable} must be a number") from error
    if not isfinite(parsed) or not 0 <= parsed <= 1:
        raise ConfigurationError(f"{variable} must be between 0 and 1")
    return parsed


@dataclass(frozen=True, slots=True)
class AppSettings:
    """Top-level application settings loaded from a supplied environment mapping."""

    environment: str
    debug: bool
    model_path: str | None
    thresholds: ThresholdSettings
    upload: UploadSettings
    inference: InferenceSettings

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "AppSettings":
        """Create settings from an injected mapping or the process environment."""
        source = os.environ if environ is None else environ
        min_mean_luminance = _parse_luminance(
            source, "COGNIVEX_MIN_MEAN_LUMINANCE", default=25.0
        )
        max_mean_luminance = _parse_luminance(
            source, "COGNIVEX_MAX_MEAN_LUMINANCE", default=230.0
        )
        if min_mean_luminance > max_mean_luminance:
            raise ConfigurationError(
                "COGNIVEX_MIN_MEAN_LUMINANCE must be less than or equal to "
                "COGNIVEX_MAX_MEAN_LUMINANCE"
            )
        return cls(
            environment=_optional_value(source, "COGNIVEX_ENVIRONMENT") or "development",
            debug=_parse_bool(source, "COGNIVEX_DEBUG", default=True),
            model_path=_optional_value(source, "COGNIVEX_MODEL_PATH"),
            thresholds=ThresholdSettings(
                model_confidence=_parse_optional_confidence(source),
                min_image_width=_parse_positive_int(
                    source, "COGNIVEX_MIN_IMAGE_WIDTH", default=640
                ),
                min_image_height=_parse_positive_int(
                    source, "COGNIVEX_MIN_IMAGE_HEIGHT", default=480
                ),
                max_image_width=_parse_positive_int(
                    source, "COGNIVEX_MAX_IMAGE_WIDTH", default=8192
                ),
                max_image_height=_parse_positive_int(
                    source, "COGNIVEX_MAX_IMAGE_HEIGHT", default=8192
                ),
                max_image_pixels=_parse_positive_int(
                    source, "COGNIVEX_MAX_IMAGE_PIXELS", default=40_000_000
                ),
                min_laplacian_variance=_parse_positive_float(
                    source, "COGNIVEX_MIN_LAPLACIAN_VARIANCE", default=80.0
                ),
                min_mean_luminance=min_mean_luminance,
                max_mean_luminance=max_mean_luminance,
                min_tile_laplacian_variance=_parse_positive_float(
                    source, "COGNIVEX_MIN_TILE_LAPLACIAN_VARIANCE", default=40.0
                ),
                min_usable_sharp_tile_ratio=_parse_ratio(
                    source, "COGNIVEX_MIN_USABLE_SHARP_TILE_RATIO", default=0.75
                ),
                min_median_luminance=_parse_luminance(
                    source, "COGNIVEX_MIN_MEDIAN_LUMINANCE", default=25.0
                ),
                dark_pixel_luminance=_parse_luminance(
                    source, "COGNIVEX_DARK_PIXEL_LUMINANCE", default=20.0
                ),
                max_dark_pixel_ratio=_parse_ratio(
                    source, "COGNIVEX_MAX_DARK_PIXEL_RATIO", default=0.65
                ),
                max_median_luminance=_parse_luminance(
                    source, "COGNIVEX_MAX_MEDIAN_LUMINANCE", default=230.0
                ),
                bright_pixel_luminance=_parse_luminance(
                    source, "COGNIVEX_BRIGHT_PIXEL_LUMINANCE", default=240.0
                ),
                max_bright_pixel_ratio=_parse_ratio(
                    source, "COGNIVEX_MAX_BRIGHT_PIXEL_RATIO", default=0.65
                ),
            ),
            upload=UploadSettings(
                max_upload_mb=_parse_positive_int(
                    source, "COGNIVEX_MAX_UPLOAD_MB", default=10
                )
            ),
            inference=InferenceSettings(
                mock_inference=_parse_bool(source, "COGNIVEX_MOCK_INFERENCE", default=True),
                localization_enabled=_parse_bool(
                    source, "COGNIVEX_LOCALIZATION_ENABLED", default=True
                ),
            ),
        )
