"""Framework-independent R7 Track C feature contracts."""

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
class TrackCFeatureContract(SerializableContract):
    """Exact ordered genomic-only predictor contract for R7 Track C."""

    expression_features: tuple[str, ...]
    mutation_features: tuple[str, ...]

    def __post_init__(self) -> None:
        _ordered_names(self.expression_features, "expression_features")
        _ordered_names(self.mutation_features, "mutation_features")
        if len(self.expression_features) != 50:
            raise ValueError("Track C requires exactly 50 expression features")
        if len(self.mutation_features) != 18:
            raise ValueError("Track C requires exactly 18 mutation features")
        if any(name.endswith("_mut") for name in self.expression_features):
            raise ValueError("expression features must not use the mutation suffix")
        if any(not name.endswith("_mut") for name in self.mutation_features):
            raise ValueError("mutation features must use the _mut suffix")
        if len(set(self.raw_features)) != 68:
            raise ValueError("Track C raw feature groups must be disjoint")

    @property
    def raw_features(self) -> tuple[str, ...]:
        return self.expression_features + self.mutation_features


@dataclass(frozen=True, slots=True)
class TrackCExclusionSummary(SerializableContract):
    """Aggregate-only Track C target eligibility for one locked split."""

    split: str
    source_rows: int
    eligible_rows: int
    nc: int
    missing: int
    unsupported: int

    def __post_init__(self) -> None:
        if self.split not in {"train", "validation", "test"}:
            raise ValueError("split must be train, validation, or test")
        values = (self.source_rows, self.eligible_rows, self.nc, self.missing, self.unsupported)
        if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in values):
            raise ValueError("Track C exclusion counts must be non-negative integers")
        if self.eligible_rows + self.nc + self.missing + self.unsupported != self.source_rows:
            raise ValueError("Track C exclusion counts must reconcile to source_rows")
