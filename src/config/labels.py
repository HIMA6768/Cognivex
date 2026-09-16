"""Canonical labels shared across application layers."""

from enum import StrEnum


class SeverityLabel(StrEnum):
    """Canonical severity labels."""

    MINOR = "minor"
    MODERATE = "moderate"
    SEVERE = "severe"


class DamageTypeLabel(StrEnum):
    """Canonical damage-type labels."""

    DENT = "dent"
    SCRATCH = "scratch"
    BROKEN_GLASS = "broken_glass"
    STRUCTURAL = "structural"

