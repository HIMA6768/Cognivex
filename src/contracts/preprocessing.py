"""Framework-independent contracts for R4 preprocessing readiness."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import StrEnum
import math

from .analysis import SerializableContract


class PreprocessingTask(StrEnum):
    """Frozen task identifiers consumed by later model increments."""

    CLINICAL_SURVIVAL = "clinical_survival"
    CLINICAL_MRNA_SURVIVAL = "clinical_mrna_survival"
    SUBTYPE_CLASSIFICATION = "subtype_classification"
    CLINICAL_MUTATION_SURVIVAL = "clinical_mutation_survival"


class PreprocessingTrack(StrEnum):
    """Frozen project track names."""

    TRACK_A = "Track A"
    TRACK_B = "Track B"
    TRACK_C = "Track C"
    TRACK_D = "Track D"


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
    MISSING_MUTATION_VALUE = "MISSING_MUTATION_VALUE"
    INVALID_MUTATION_VALUE = "INVALID_MUTATION_VALUE"
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
class SplitEligibilityCount(SerializableContract):
    """Aggregate task eligibility within one immutable manifest split."""

    split: str
    eligible_count: int
    excluded_count: int

    def __post_init__(self) -> None:
        if self.split not in {"train", "validation", "test"}:
            raise ValueError("split must be train, validation, or test")
        _require_non_negative_integer(self.eligible_count, "eligible_count")
        _require_non_negative_integer(self.excluded_count, "excluded_count")


@dataclass(frozen=True, slots=True)
class MutationFeatureSelection(SerializableContract):
    """One fitted mutation-frequency decision without patient-level values."""

    raw_column: str
    gene: str
    derived_feature_name: str
    prevalence: float
    retained: bool

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.raw_column, "raw_column"),
            (self.gene, "gene"),
            (self.derived_feature_name, "derived_feature_name"),
        ):
            _require_text(value, field_name)
        if not self.raw_column.endswith("_mut"):
            raise ValueError("raw_column must end with _mut")
        if self.gene != self.raw_column.removesuffix("_mut"):
            raise ValueError("gene must match raw_column")
        if self.derived_feature_name != f"{self.raw_column}_present":
            raise ValueError("derived_feature_name must use the <raw_column>_present convention")
        if (
            not isinstance(self.prevalence, (int, float))
            or isinstance(self.prevalence, bool)
            or not math.isfinite(float(self.prevalence))
            or not 0 <= float(self.prevalence) <= 1
        ):
            raise ValueError("prevalence must be a finite fraction from 0 through 1")
        if not isinstance(self.retained, bool):
            raise TypeError("retained must be a bool")


@dataclass(frozen=True, slots=True)
class MutationSelectionMetadata(SerializableContract):
    """Aggregate fitted evidence for one fold-local mutation selector."""

    threshold: float
    comparison: str
    fit_row_count: int
    features: tuple[MutationFeatureSelection, ...]
    retained_genes: tuple[str, ...] = field(init=False)
    excluded_genes: tuple[str, ...] = field(init=False)
    retained_feature_names: tuple[str, ...] = field(init=False)

    def __post_init__(self) -> None:
        if (
            not isinstance(self.threshold, (int, float))
            or isinstance(self.threshold, bool)
            or not math.isfinite(float(self.threshold))
            or not 0 <= float(self.threshold) <= 1
        ):
            raise ValueError("threshold must be a finite fraction from 0 through 1")
        if self.comparison != "greater_than_or_equal":
            raise ValueError("comparison must be greater_than_or_equal")
        _require_non_negative_integer(self.fit_row_count, "fit_row_count")
        if not isinstance(self.features, tuple) or not self.features or not all(
            isinstance(item, MutationFeatureSelection) for item in self.features
        ):
            raise TypeError("features must be a non-empty ordered tuple of MutationFeatureSelection values")
        raw_columns = tuple(item.raw_column for item in self.features)
        if len(raw_columns) != len(set(raw_columns)):
            raise ValueError("mutation selection raw columns must be unique")
        retained = tuple(item for item in self.features if item.retained)
        excluded = tuple(item for item in self.features if not item.retained)
        object.__setattr__(self, "retained_genes", tuple(item.gene for item in retained))
        object.__setattr__(self, "excluded_genes", tuple(item.gene for item in excluded))
        object.__setattr__(
            self,
            "retained_feature_names",
            tuple(item.derived_feature_name for item in retained),
        )


@dataclass(frozen=True, slots=True)
class MutationPreprocessingMetadata(SerializableContract):
    """Typed Track D representation, selection, and burden policies."""

    representation_policy: str
    source_feature_names: tuple[str, ...]
    selection: MutationSelectionMetadata
    burden_source_feature_count: int
    burden_feature_name: str
    burden_transformation: str

    def __post_init__(self) -> None:
        _require_text(self.representation_policy, "representation_policy")
        _require_text_tuple(self.source_feature_names, "source_feature_names")
        if len(self.source_feature_names) != len(set(self.source_feature_names)) or not all(
            name.endswith("_mut") for name in self.source_feature_names
        ):
            raise ValueError("source_feature_names must be unique raw _mut columns")
        if not isinstance(self.selection, MutationSelectionMetadata):
            raise TypeError("selection must be MutationSelectionMetadata")
        if tuple(item.raw_column for item in self.selection.features) != self.source_feature_names:
            raise ValueError("selection features must match source_feature_names in order")
        _require_non_negative_integer(self.burden_source_feature_count, "burden_source_feature_count")
        if self.burden_source_feature_count != len(self.source_feature_names):
            raise ValueError("burden_source_feature_count must match source_feature_names")
        if self.burden_feature_name != "mutation_burden_log1p":
            raise ValueError("burden_feature_name must be mutation_burden_log1p")
        _require_text(self.burden_transformation, "burden_transformation")


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
    split_counts: tuple[SplitEligibilityCount, ...] = ()
    mutation_metadata: MutationPreprocessingMetadata | None = None
    standardized_continuous_feature_names: tuple[str, ...] = ()
    unscaled_binary_feature_names: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.task, PreprocessingTask):
            raise TypeError("task must be a PreprocessingTask")
        if not isinstance(self.track, PreprocessingTrack):
            raise TypeError("track must be a PreprocessingTrack")
        expected_track = {
            PreprocessingTask.CLINICAL_SURVIVAL: PreprocessingTrack.TRACK_A,
            PreprocessingTask.CLINICAL_MRNA_SURVIVAL: PreprocessingTrack.TRACK_B,
            PreprocessingTask.SUBTYPE_CLASSIFICATION: PreprocessingTrack.TRACK_C,
            PreprocessingTask.CLINICAL_MUTATION_SURVIVAL: PreprocessingTrack.TRACK_D,
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
        if not isinstance(self.split_counts, tuple) or not all(
            isinstance(item, SplitEligibilityCount) for item in self.split_counts
        ):
            raise TypeError("split_counts must be an ordered tuple of SplitEligibilityCount values")
        for value, field_name in (
            (self.standardized_continuous_feature_names, "standardized_continuous_feature_names"),
            (self.unscaled_binary_feature_names, "unscaled_binary_feature_names"),
        ):
            _require_text_tuple(value, field_name)
        if self.task is PreprocessingTask.CLINICAL_MUTATION_SURVIVAL:
            if not isinstance(self.mutation_metadata, MutationPreprocessingMetadata):
                raise TypeError("Track D requires mutation_metadata")
            if self.mrna_feature_names:
                raise ValueError("Track D cannot include mRNA feature names")
            standardized = self.standardized_continuous_feature_names
            unscaled = self.unscaled_binary_feature_names
            if set(standardized) & set(unscaled) or set(standardized + unscaled) != set(
                self.final_feature_names
            ) or len(standardized) + len(unscaled) != len(self.final_feature_names):
                raise ValueError("Track D scaling groups must form an exact disjoint final feature partition")
            if not set(self.mutation_metadata.selection.retained_feature_names).issubset(unscaled):
                raise ValueError("retained mutation features must belong to the unscaled feature partition")
            if self.mutation_metadata.burden_feature_name not in standardized:
                raise ValueError("mutation burden must belong to the standardized feature partition")
        elif self.mutation_metadata is not None:
            raise ValueError("only Track D may carry mutation_metadata")


@dataclass(frozen=True, slots=True)
class CanonicalPreprocessingReport(SerializableContract):
    """Aggregate read-only evidence that canonical R4 preprocessing is ready."""

    tasks: tuple[PreprocessingMetadata, ...]
    tumor_size_missing_indicator_count: int
    er_ihc_missing_indicator_count: int
    mutation_feature_count: int
    forbidden_feature_count: int
    train_only_fit_verified: bool
    raw_sha256: str
    prepared_sha256: str
    canonical_artifacts_unchanged: bool

    def __post_init__(self) -> None:
        if not isinstance(self.tasks, tuple) or not all(
            isinstance(item, PreprocessingMetadata) for item in self.tasks
        ):
            raise TypeError("tasks must be an ordered tuple of PreprocessingMetadata values")
        if tuple(item.task for item in self.tasks) != tuple(PreprocessingTask):
            raise ValueError("tasks must contain Track A, Track B, Track C, and Track D metadata in task order")
        for value, field_name in (
            (self.tumor_size_missing_indicator_count, "tumor_size_missing_indicator_count"),
            (self.er_ihc_missing_indicator_count, "er_ihc_missing_indicator_count"),
            (self.mutation_feature_count, "mutation_feature_count"),
            (self.forbidden_feature_count, "forbidden_feature_count"),
        ):
            _require_non_negative_integer(value, field_name)
        for value, field_name in (
            (self.train_only_fit_verified, "train_only_fit_verified"),
            (self.canonical_artifacts_unchanged, "canonical_artifacts_unchanged"),
        ):
            if not isinstance(value, bool):
                raise TypeError(f"{field_name} must be a bool")
        for value, field_name in (
            (self.raw_sha256, "raw_sha256"),
            (self.prepared_sha256, "prepared_sha256"),
        ):
            if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
                raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
