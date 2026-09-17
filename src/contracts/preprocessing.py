"""Framework-independent contracts for R4 preprocessing readiness."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import StrEnum

from .analysis import SerializableContract


class PreprocessingTask(StrEnum):
    """Frozen task identifiers consumed by later model increments."""

    CLINICAL_SURVIVAL = "clinical_survival"
    CLINICAL_MRNA_SURVIVAL = "clinical_mrna_survival"
    SUBTYPE_CLASSIFICATION = "subtype_classification"


class PreprocessingTrack(StrEnum):
    """Frozen project track names."""

    TRACK_A = "Track A"
    TRACK_B = "Track B"
    TRACK_C = "Track C"


class EligibilityReasonCode(StrEnum):
    """Stable task-exclusion reasons that never become predictors."""

    MISSING_SURVIVAL_DURATION = "MISSING_SURVIVAL_DURATION"
    NON_NUMERIC_SURVIVAL_DURATION = "NON_NUMERIC_SURVIVAL_DURATION"
    NON_FINITE_SURVIVAL_DURATION = "NON_FINITE_SURVIVAL_DURATION"
    NON_POSITIVE_SURVIVAL_DURATION = "NON_POSITIVE_SURVIVAL_DURATION"
    MISSING_SURVIVAL_EVENT = "MISSING_SURVIVAL_EVENT"
    INVALID_SURVIVAL_EVENT = "INVALID_SURVIVAL_EVENT"
    INVALID_LOCKED_SPLIT = "INVALID_LOCKED_SPLIT"
    MISSING_MRNA_VALUE = "MISSING_MRNA_VALUE"
    NON_NUMERIC_MRNA_VALUE = "NON_NUMERIC_MRNA_VALUE"
    NON_FINITE_MRNA_VALUE = "NON_FINITE_MRNA_VALUE"
    MISSING_SUBTYPE = "MISSING_SUBTYPE"
    NC_SUBTYPE = "NC_SUBTYPE"
    UNSUPPORTED_SUBTYPE = "UNSUPPORTED_SUBTYPE"


def _require_non_negative_integer(value: int, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_text_tuple(value: tuple[str, ...], field_name: str) -> None:
    if not isinstance(value, tuple) or not all(isinstance(item, str) and item.strip() for item in value):
        raise TypeError(f"{field_name} must be an ordered tuple of non-empty strings")


@dataclass(frozen=True, slots=True)
class ExclusionCount(SerializableContract):
    """Aggregate number of task rows carrying one exclusion reason."""

    reason: EligibilityReasonCode
    count: int

    def __post_init__(self) -> None:
        if not isinstance(self.reason, EligibilityReasonCode):
            raise TypeError("reason must be an EligibilityReasonCode")
        _require_non_negative_integer(self.count, "count")


@dataclass(frozen=True, slots=True)
class EligibilityResult(SerializableContract):
    """Row-aligned task mask and reason tuples without patient identifiers."""

    mask: tuple[bool, ...]
    reasons: tuple[tuple[EligibilityReasonCode, ...], ...]
    eligible_count: int = field(init=False)
    excluded_count: int = field(init=False)
    exclusion_counts: tuple[ExclusionCount, ...] = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.mask, tuple) or not all(isinstance(value, bool) for value in self.mask):
            raise TypeError("mask must be an ordered tuple of bool values")
        if not isinstance(self.reasons, tuple) or len(self.mask) != len(self.reasons):
            raise ValueError("mask and reasons must be aligned ordered tuples")
        for included, row_reasons in zip(self.mask, self.reasons, strict=True):
            if not isinstance(row_reasons, tuple) or not all(
                isinstance(reason, EligibilityReasonCode) for reason in row_reasons
            ):
                raise TypeError("each reasons item must be a tuple of EligibilityReasonCode values")
            if included and row_reasons:
                raise ValueError("eligible rows cannot have exclusion reasons")
            if not included and not row_reasons:
                raise ValueError("excluded rows must have at least one exclusion reason")

        counts = Counter(reason for row_reasons in self.reasons for reason in row_reasons)
        object.__setattr__(self, "eligible_count", sum(self.mask))
        object.__setattr__(self, "excluded_count", len(self.mask) - sum(self.mask))
        object.__setattr__(
            self,
            "exclusion_counts",
            tuple(ExclusionCount(reason, counts[reason]) for reason in sorted(counts, key=lambda item: item.value)),
        )


@dataclass(frozen=True, slots=True)
class PreprocessingMetadata(SerializableContract):
    """Aggregate, serializable explanation of one fitted preprocessing contract."""

    task: PreprocessingTask
    track: PreprocessingTrack
    source_dataset: str
    source_version: str
    fitted_on_split: str
    eligible_row_count: int
    excluded_row_count: int
    exclusion_counts: tuple[ExclusionCount, ...]
    raw_feature_count: int
    transformed_feature_count: int
    clinical_feature_names: tuple[str, ...]
    mrna_feature_names: tuple[str, ...]
    final_feature_names: tuple[str, ...]
    imputation_strategy: str
    missing_indicator_strategy: str
    categorical_encoding_strategy: str
    scaling_strategy: str
    mutation_policy: str
    nc_policy: str
    zero_duration_policy: str
    forbidden_feature_guard_passed: bool

    def __post_init__(self) -> None:
        if not isinstance(self.task, PreprocessingTask):
            raise TypeError("task must be a PreprocessingTask")
        if not isinstance(self.track, PreprocessingTrack):
            raise TypeError("track must be a PreprocessingTrack")
        expected_track = {
            PreprocessingTask.CLINICAL_SURVIVAL: PreprocessingTrack.TRACK_A,
            PreprocessingTask.CLINICAL_MRNA_SURVIVAL: PreprocessingTrack.TRACK_B,
            PreprocessingTask.SUBTYPE_CLASSIFICATION: PreprocessingTrack.TRACK_C,
        }[self.task]
        if self.track is not expected_track:
            raise ValueError("track must match task")
        for value, field_name in (
            (self.source_dataset, "source_dataset"),
            (self.source_version, "source_version"),
            (self.imputation_strategy, "imputation_strategy"),
            (self.missing_indicator_strategy, "missing_indicator_strategy"),
            (self.categorical_encoding_strategy, "categorical_encoding_strategy"),
            (self.scaling_strategy, "scaling_strategy"),
            (self.mutation_policy, "mutation_policy"),
            (self.nc_policy, "nc_policy"),
            (self.zero_duration_policy, "zero_duration_policy"),
        ):
            _require_text(value, field_name)
        if self.fitted_on_split != "train":
            raise ValueError("fitted_on_split must be train")
        for value, field_name in (
            (self.eligible_row_count, "eligible_row_count"),
            (self.excluded_row_count, "excluded_row_count"),
            (self.raw_feature_count, "raw_feature_count"),
            (self.transformed_feature_count, "transformed_feature_count"),
        ):
            _require_non_negative_integer(value, field_name)
        if not isinstance(self.exclusion_counts, tuple) or not all(
            isinstance(item, ExclusionCount) for item in self.exclusion_counts
        ):
            raise TypeError("exclusion_counts must be an ordered tuple of ExclusionCount values")
        for value, field_name in (
            (self.clinical_feature_names, "clinical_feature_names"),
            (self.mrna_feature_names, "mrna_feature_names"),
            (self.final_feature_names, "final_feature_names"),
        ):
            _require_text_tuple(value, field_name)
        if self.transformed_feature_count != len(self.final_feature_names):
            raise ValueError("transformed_feature_count must match final_feature_names")
        if not isinstance(self.forbidden_feature_guard_passed, bool):
            raise TypeError("forbidden_feature_guard_passed must be a bool")
