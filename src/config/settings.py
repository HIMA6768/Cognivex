"""Side-effect-free, domain-neutral application settings."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import os


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


@dataclass(frozen=True, slots=True)
class AppSettings:
    """Application-wide settings that do not assume a dataset or model."""

    environment: str
    debug: bool

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "AppSettings":
        """Load settings from an injected mapping or the process environment."""
        source = os.environ if environ is None else environ
        return cls(
            environment=_optional_value(source, "COGNIVEX_ENVIRONMENT") or "development",
            debug=_parse_bool(source, "COGNIVEX_DEBUG", default=True),
        )
