"""Framework-independent R6 Track B feature contracts."""

from __future__ import annotations

from dataclasses import dataclass

from .analysis import SerializableContract


def _ordered_names(values: tuple[str, ...], field: str) -> None:
    if not isinstance(values, tuple) or not values:
        raise ValueError(f"{field} must be a non-empty ordered tuple")
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError(f"{field} must contain non-empty strings")
    if len(values) != len(set(values)):
        raise ValueError(f"{field} must contain unique names")


@dataclass(frozen=True, slots=True)
class TrackBFeatureContract(SerializableContract):
    """Exact ordered raw predictor contract for R6 Track B."""

    clinical_features: tuple[str, ...]
    expression_features: tuple[str, ...]
    mutation_features: tuple[str, ...]

    def __post_init__(self) -> None:
        for field in ("clinical_features", "expression_features", "mutation_features"):
            _ordered_names(getattr(self, field), field)
        if len(self.clinical_features) != 7:
            raise ValueError("Track B requires exactly 7 clinical features")
        if len(self.expression_features) != 50:
            raise ValueError("Track B requires exactly 50 expression features")
        if len(self.mutation_features) != 18:
            raise ValueError("Track B requires exactly 18 mutation features")
        if any(name.endswith("_mut") for name in self.expression_features):
            raise ValueError("expression features must not use the mutation suffix")
        if any(not name.endswith("_mut") for name in self.mutation_features):
            raise ValueError("mutation features must use the _mut suffix")
        if len(set(self.raw_features)) != 75:
            raise ValueError("Track B raw feature groups must be disjoint")

    @property
    def raw_features(self) -> tuple[str, ...]:
        return self.clinical_features + self.expression_features + self.mutation_features

