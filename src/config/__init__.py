"""Configuration contracts for the Cognivex application."""

from .labels import DamageTypeLabel, SeverityLabel
from .inference import InferenceSettings
from .settings import AppSettings, ConfigurationError
from .thresholds import ThresholdSettings
from .uploads import UploadSettings

__all__ = [
    "AppSettings",
    "ConfigurationError",
    "DamageTypeLabel",
    "InferenceSettings",
    "SeverityLabel",
    "ThresholdSettings",
    "UploadSettings",
]
