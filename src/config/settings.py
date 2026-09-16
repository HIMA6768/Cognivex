"""Environment-backed application settings."""

from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
import os

from .thresholds import ThresholdSettings


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


@dataclass(frozen=True, slots=True)
class AppSettings:
    """Top-level application settings loaded from a supplied environment mapping."""

    environment: str
    debug: bool
    model_path: str | None
    thresholds: ThresholdSettings

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "AppSettings":
        """Create settings from an injected mapping or the process environment."""
        source = os.environ if environ is None else environ
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
            ),
        )
