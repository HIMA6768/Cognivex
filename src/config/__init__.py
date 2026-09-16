"""Configuration contracts for the Cognivex application."""

from .labels import DamageTypeLabel, SeverityLabel
from .settings import AppSettings, ConfigurationError
from .thresholds import ThresholdSettings

__all__ = [
    "AppSettings",
    "ConfigurationError",
    "DamageTypeLabel",
    "SeverityLabel",
    "ThresholdSettings",
]

