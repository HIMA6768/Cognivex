"""Domain-neutral configuration contracts for the Cognivex application."""

from .settings import AppSettings, ConfigurationError

__all__ = ["AppSettings", "ConfigurationError"]
