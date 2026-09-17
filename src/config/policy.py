"""Configuration for the provisional, development-only P8 routing policy."""

from dataclasses import dataclass
from math import isfinite

from .labels import DamageTypeLabel


DEFAULT_CONFLICT_PAIRS: tuple[tuple[DamageTypeLabel, DamageTypeLabel], ...] = (
    (DamageTypeLabel.SCRATCH, DamageTypeLabel.STRUCTURAL),
)


@dataclass(frozen=True, slots=True)
class PolicySettings:
    """PROVISIONAL DEVELOPMENT POLICY values pending calibration and outcome validation."""

    min_severity_score: float = 0.75
    min_damage_type_score: float = 0.75
    min_localization_conflict_score: float = 0.80
    conflict_pairs: tuple[tuple[DamageTypeLabel, DamageTypeLabel], ...] = DEFAULT_CONFLICT_PAIRS

    def __post_init__(self) -> None:
        for field_name in (
            "min_severity_score",
            "min_damage_type_score",
            "min_localization_conflict_score",
        ):
            value = getattr(self, field_name)
            if not isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{field_name} must be a finite value between 0 and 1")
        if not isinstance(self.conflict_pairs, tuple):
            raise TypeError("conflict_pairs must be an ordered tuple")
        for classifier_label, localization_label in self.conflict_pairs:
            if not isinstance(classifier_label, DamageTypeLabel) or not isinstance(
                localization_label, DamageTypeLabel
            ):
                raise TypeError("conflict pairs must contain canonical damage-type labels")
            if classifier_label is localization_label:
                raise ValueError("conflict pairs must contain different canonical damage-type labels")
