"""Central, non-clinical engineering heuristics for R3 quality reporting."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class QualityRules:
    """Read-only reporting rules; they never reject or modify records by themselves."""

    suspicious_survival_months: float = 1200.0

    def __post_init__(self) -> None:
        if (
            not isinstance(self.suspicious_survival_months, (float, int))
            or isinstance(self.suspicious_survival_months, bool)
            or self.suspicious_survival_months <= 0
        ):
            raise ValueError("suspicious_survival_months must be a positive number")


DEFAULT_QUALITY_RULES = QualityRules()
