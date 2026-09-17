"""Framework-independent R1 contracts for pending biomedical analysis."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum, StrEnum
from pathlib import Path
from typing import Any


def _serializable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return value.as_posix()
    if is_dataclass(value):
        return {key: _serializable(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_serializable(item) for item in value]
    if isinstance(value, list):
        return [_serializable(item) for item in value]
    if isinstance(value, dict):
        return {key: _serializable(item) for key, item in value.items()}
    return value


class SerializableContract:
    """Expose JSON-compatible dictionaries without a framework serializer."""

    def to_dict(self) -> dict[str, Any]:
        return _serializable(self)


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_optional_text(value: str | None, field_name: str) -> None:
    if value is not None:
        _require_text(value, field_name)


def _require_optional_count(value: int | None, field_name: str) -> None:
    if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
        raise ValueError(f"{field_name} must be a non-negative integer or None")


class AnalysisStatus(StrEnum):
    """Availability states independent of any modeling result."""

    PENDING_DATA = "PENDING_DATA"
    DATA_READY = "DATA_READY"
    DATA_INVALID = "DATA_INVALID"
    PENDING_MODEL = "PENDING_MODEL"


class ValidationIssueSeverity(StrEnum):
    """Stable data-quality issue levels for future ingestion increments."""

    ERROR = "ERROR"
    WARNING = "WARNING"
    INFORMATION = "INFORMATION"


class DataQualitySeverity(StrEnum):
    """Severity of a downstream data-engineering quality finding."""

    ERROR = "ERROR"
    WARNING = "WARNING"
    INFORMATION = "INFORMATION"


class DataQualityStatus(StrEnum):
    """Engineering readiness, never a clinical-quality judgment."""

    DATA_QUALITY_READY = "DATA_QUALITY_READY"
    DATA_QUALITY_READY_WITH_WARNINGS = "DATA_QUALITY_READY_WITH_WARNINGS"
    DATA_QUALITY_BLOCKED = "DATA_QUALITY_BLOCKED"


def _require_fraction(value: float | None, field_name: str) -> None:
    if value is None:
        return
    if not isinstance(value, (float, int)) or isinstance(value, bool) or not 0 <= value <= 1:
        raise ValueError(f"{field_name} must be a fraction from 0 through 1 or None")


@dataclass(frozen=True, slots=True)
class DataQualityFinding(SerializableContract):
    """A stable, aggregate-only finding for later engineering work."""

    code: str
    severity: DataQualitySeverity
    title: str
    message: str
    affected_count: int
    affected_fraction: float | None
    subject: str | None
    recommendation: str

    def __post_init__(self) -> None:
        _require_text(self.code, "code")
        if not isinstance(self.severity, DataQualitySeverity):
            raise TypeError("severity must be a DataQualitySeverity")
        _require_text(self.title, "title")
        _require_text(self.message, "message")
        _require_optional_count(self.affected_count, "affected_count")
        _require_fraction(self.affected_fraction, "affected_fraction")
        _require_optional_text(self.subject, "subject")
        _require_text(self.recommendation, "recommendation")


@dataclass(frozen=True, slots=True)
class CategoryCount(SerializableContract):
    """A named aggregate count and its fraction of the scanned cohort."""

    label: str
    count: int
    fraction: float | None

    def __post_init__(self) -> None:
        _require_text(self.label, "label")
        _require_optional_count(self.count, "count")
        _require_fraction(self.fraction, "fraction")


@dataclass(frozen=True, slots=True)
class FieldQualitySummary(SerializableContract):
    """Aggregate missingness and invalid-value counts for one clinical field."""

    field_name: str
    total_count: int
    missing_count: int
    invalid_count: int

    def __post_init__(self) -> None:
        _require_text(self.field_name, "field_name")
        for value, field_name in (
            (self.total_count, "total_count"),
            (self.missing_count, "missing_count"),
            (self.invalid_count, "invalid_count"),
        ):
            _require_optional_count(value, field_name)
        if self.missing_count + self.invalid_count > self.total_count:
            raise ValueError("missing_count plus invalid_count cannot exceed total_count")


@dataclass(frozen=True, slots=True)
class SurvivalQualitySummary(SerializableContract):
    """Aggregate checks for canonical survival duration and event fields."""

    time_column: str
    event_column: str
    total_count: int
    event_count: int
    censored_count: int
    missing_time_count: int
    non_numeric_time_count: int
    negative_time_count: int
    zero_time_count: int
    suspicious_time_count: int
    missing_event_count: int
    invalid_event_count: int

    def __post_init__(self) -> None:
        _require_text(self.time_column, "time_column")
        _require_text(self.event_column, "event_column")
        for value, field_name in (
            (self.total_count, "total_count"),
            (self.event_count, "event_count"),
            (self.censored_count, "censored_count"),
            (self.missing_time_count, "missing_time_count"),
            (self.non_numeric_time_count, "non_numeric_time_count"),
            (self.negative_time_count, "negative_time_count"),
            (self.zero_time_count, "zero_time_count"),
            (self.suspicious_time_count, "suspicious_time_count"),
            (self.missing_event_count, "missing_event_count"),
            (self.invalid_event_count, "invalid_event_count"),
        ):
            _require_optional_count(value, field_name)
        if self.event_count + self.censored_count > self.total_count:
            raise ValueError("event and censored counts cannot exceed total_count")


@dataclass(frozen=True, slots=True)
class SplitQualitySummary(SerializableContract):
    """Aggregate event and subtype distribution for one locked split."""

    split: str
    patient_count: int
    event_count: int
    censored_count: int
    subtype_counts: tuple[CategoryCount, ...]

    def __post_init__(self) -> None:
        _require_text(self.split, "split")
        for value, field_name in (
            (self.patient_count, "patient_count"),
            (self.event_count, "event_count"),
            (self.censored_count, "censored_count"),
        ):
            _require_optional_count(value, field_name)
        if self.event_count + self.censored_count > self.patient_count:
            raise ValueError("event and censored counts cannot exceed patient_count")
        if not isinstance(self.subtype_counts, tuple) or not all(
            isinstance(count, CategoryCount) for count in self.subtype_counts
        ):
            raise TypeError("subtype_counts must be an ordered tuple of CategoryCount values")


@dataclass(frozen=True, slots=True)
class SubtypeQualitySummary(SerializableContract):
    """Aggregate subtype mapping, missingness, and NC-policy state."""

    taxonomy_column: str
    class_counts: tuple[CategoryCount, ...]
    nc_count: int
    missing_count: int
    unexpected_count: int
    nc_policy: str

    def __post_init__(self) -> None:
        _require_text(self.taxonomy_column, "taxonomy_column")
        if not isinstance(self.class_counts, tuple) or not all(
            isinstance(count, CategoryCount) for count in self.class_counts
        ):
            raise TypeError("class_counts must be an ordered tuple of CategoryCount values")
        for value, field_name in (
            (self.nc_count, "nc_count"),
            (self.missing_count, "missing_count"),
            (self.unexpected_count, "unexpected_count"),
        ):
            _require_optional_count(value, field_name)
        _require_text(self.nc_policy, "nc_policy")


@dataclass(frozen=True, slots=True)
class GenomicQualitySummary(SerializableContract):
    """Aggregate integrity and missingness metrics for one genomic feature group."""

    group_name: str
    expected_feature_count: int
    present_feature_count: int
    total_value_count: int
    missing_value_count: int
    non_numeric_value_count: int
    infinite_value_count: int
    zero_variance_feature_count: int

    def __post_init__(self) -> None:
        _require_text(self.group_name, "group_name")
        for value, field_name in (
            (self.expected_feature_count, "expected_feature_count"),
            (self.present_feature_count, "present_feature_count"),
            (self.total_value_count, "total_value_count"),
            (self.missing_value_count, "missing_value_count"),
            (self.non_numeric_value_count, "non_numeric_value_count"),
            (self.infinite_value_count, "infinite_value_count"),
            (self.zero_variance_feature_count, "zero_variance_feature_count"),
        ):
            _require_optional_count(value, field_name)
        if self.present_feature_count > self.expected_feature_count:
            raise ValueError("present_feature_count cannot exceed expected_feature_count")
        if self.missing_value_count + self.non_numeric_value_count + self.infinite_value_count > self.total_value_count:
            raise ValueError("invalid genomic values cannot exceed total_value_count")


@dataclass(frozen=True, slots=True)
class DataQualityReport(SerializableContract):
    """Deterministic aggregate data-quality report for engineering readiness."""

    status: DataQualityStatus
    findings: tuple[DataQualityFinding, ...]
    cohort_size: int | None
    error_count: int
    warning_count: int
    information_count: int
    survival: SurvivalQualitySummary | None = None
    clinical_missingness: tuple[FieldQualitySummary, ...] = ()
    split_summaries: tuple[SplitQualitySummary, ...] = ()
    subtype: SubtypeQualitySummary | None = None
    genomic_summaries: tuple[GenomicQualitySummary, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, DataQualityStatus):
            raise TypeError("status must be a DataQualityStatus")
        if not isinstance(self.findings, tuple) or not all(
            isinstance(finding, DataQualityFinding) for finding in self.findings
        ):
            raise TypeError("findings must be an ordered tuple of DataQualityFinding values")
        _require_optional_count(self.cohort_size, "cohort_size")
        expected_counts = {
            DataQualitySeverity.ERROR: self.error_count,
            DataQualitySeverity.WARNING: self.warning_count,
            DataQualitySeverity.INFORMATION: self.information_count,
        }
        for severity, count in expected_counts.items():
            _require_optional_count(count, f"{severity.value.lower()}_count")
            if count != sum(finding.severity is severity for finding in self.findings):
                raise ValueError(f"{severity.value.lower()}_count must match findings")
        if self.survival is not None and not isinstance(self.survival, SurvivalQualitySummary):
            raise TypeError("survival must be SurvivalQualitySummary or None")
        if not isinstance(self.clinical_missingness, tuple) or not all(
            isinstance(summary, FieldQualitySummary) for summary in self.clinical_missingness
        ):
            raise TypeError("clinical_missingness must be an ordered tuple of FieldQualitySummary values")
        if not isinstance(self.split_summaries, tuple) or not all(
            isinstance(summary, SplitQualitySummary) for summary in self.split_summaries
        ):
            raise TypeError("split_summaries must be an ordered tuple of SplitQualitySummary values")
        if self.subtype is not None and not isinstance(self.subtype, SubtypeQualitySummary):
            raise TypeError("subtype must be SubtypeQualitySummary or None")
        if not isinstance(self.genomic_summaries, tuple) or not all(
            isinstance(summary, GenomicQualitySummary) for summary in self.genomic_summaries
        ):
            raise TypeError("genomic_summaries must be an ordered tuple of GenomicQualitySummary values")


@dataclass(frozen=True, slots=True)
class DatasetValidationIssue(SerializableContract):
    """A typed, user-safe validation observation."""

    code: str
    severity: ValidationIssueSeverity
    message: str

    def __post_init__(self) -> None:
        _require_text(self.code, "code")
        if not isinstance(self.severity, ValidationIssueSeverity):
            raise TypeError("severity must be a ValidationIssueSeverity")
        _require_text(self.message, "message")


@dataclass(frozen=True, slots=True)
class DatasetValidationReport(SerializableContract):
    """Dataset-validation skeleton; R1 can only report pending data."""

    status: AnalysisStatus
    message: str
    issues: tuple[DatasetValidationIssue, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, AnalysisStatus):
            raise TypeError("status must be an AnalysisStatus")
        _require_text(self.message, "message")
        if not isinstance(self.issues, tuple) or not all(
            isinstance(issue, DatasetValidationIssue) for issue in self.issues
        ):
            raise TypeError("issues must be an ordered tuple of DatasetValidationIssue values")


@dataclass(frozen=True, slots=True)
class CohortSplitSummary(SerializableContract):
    """Aggregate patient counts for the locked handoff partitions."""

    train_patients: int
    validation_patients: int
    test_patients: int

    def __post_init__(self) -> None:
        _require_optional_count(self.train_patients, "train_patients")
        _require_optional_count(self.validation_patients, "validation_patients")
        _require_optional_count(self.test_patients, "test_patients")


@dataclass(frozen=True, slots=True)
class CohortSummary(SerializableContract):
    """Aggregate cohort counts without exposing source records."""

    status: AnalysisStatus
    message: str
    clinical_records: int | None = None
    patient_records: int | None = None
    genomic_samples: int | None = None
    matched_samples: int | None = None
    split_summary: CohortSplitSummary | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, AnalysisStatus):
            raise TypeError("status must be an AnalysisStatus")
        _require_text(self.message, "message")
        _require_optional_count(self.clinical_records, "clinical_records")
        _require_optional_count(self.patient_records, "patient_records")
        _require_optional_count(self.genomic_samples, "genomic_samples")
        _require_optional_count(self.matched_samples, "matched_samples")
        if self.split_summary is not None and not isinstance(self.split_summary, CohortSplitSummary):
            raise TypeError("split_summary must be CohortSplitSummary or None")


@dataclass(frozen=True, slots=True)
class DataArtifactStatus(SerializableContract):
    """Checksum status for a repository-owned handoff artifact."""

    source_name: str
    relative_path: Path
    checksum_verified: bool

    def __post_init__(self) -> None:
        _require_text(self.source_name, "source_name")
        if not isinstance(self.relative_path, Path) or self.relative_path.is_absolute():
            raise ValueError("relative_path must be a relative Path")
        if not isinstance(self.checksum_verified, bool):
            raise TypeError("checksum_verified must be a bool")


@dataclass(frozen=True, slots=True)
class DatasetMetadata(SerializableContract):
    """Validated descriptive metadata without source rows or model results."""

    dataset_name: str
    column_count: int
    clinical_feature_count: int
    mrna_feature_count: int
    mutation_feature_count: int
    clinical_feature_names: tuple[str, ...]
    subtype_labels: tuple[str, ...]
    subtype_nc_policy: str
    prepared_dataset_path: Path

    def __post_init__(self) -> None:
        _require_text(self.dataset_name, "dataset_name")
        for value, field_name in (
            (self.column_count, "column_count"),
            (self.clinical_feature_count, "clinical_feature_count"),
            (self.mrna_feature_count, "mrna_feature_count"),
            (self.mutation_feature_count, "mutation_feature_count"),
        ):
            _require_optional_count(value, field_name)
        if not isinstance(self.clinical_feature_names, tuple) or not self.clinical_feature_names:
            raise ValueError("clinical_feature_names must be a non-empty ordered tuple")
        if not all(isinstance(name, str) and name.strip() for name in self.clinical_feature_names):
            raise ValueError("clinical_feature_names must contain non-empty strings")
        if not isinstance(self.subtype_labels, tuple) or not self.subtype_labels:
            raise ValueError("subtype_labels must be a non-empty ordered tuple")
        if not all(isinstance(label, str) and label.strip() for label in self.subtype_labels):
            raise ValueError("subtype_labels must contain non-empty strings")
        _require_text(self.subtype_nc_policy, "subtype_nc_policy")
        if not isinstance(self.prepared_dataset_path, Path) or self.prepared_dataset_path.is_absolute():
            raise ValueError("prepared_dataset_path must be a relative Path")


@dataclass(frozen=True, slots=True)
class MetabricIngestionResult(SerializableContract):
    """Validated aggregate-only result from the canonical METABRIC package."""

    validation: DatasetValidationReport
    cohort: CohortSummary
    metadata: DatasetMetadata | None
    artifacts: tuple[DataArtifactStatus, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.validation, DatasetValidationReport):
            raise TypeError("validation must be DatasetValidationReport")
        if not isinstance(self.cohort, CohortSummary):
            raise TypeError("cohort must be CohortSummary")
        if self.metadata is not None and not isinstance(self.metadata, DatasetMetadata):
            raise TypeError("metadata must be DatasetMetadata or None")
        if not isinstance(self.artifacts, tuple) or not all(
            isinstance(artifact, DataArtifactStatus) for artifact in self.artifacts
        ):
            raise TypeError("artifacts must be an ordered tuple of DataArtifactStatus values")


@dataclass(frozen=True, slots=True)
class ModelMetadata(SerializableContract):
    """Unresolved model provenance fields pending a verified model handoff."""

    name: str | None
    version: str | None
    experiment_id: str | None
    preprocessing_version: str | None
    mock: bool

    def __post_init__(self) -> None:
        _require_optional_text(self.name, "name")
        _require_optional_text(self.version, "version")
        _require_optional_text(self.experiment_id, "experiment_id")
        _require_optional_text(self.preprocessing_version, "preprocessing_version")
        if not isinstance(self.mock, bool):
            raise TypeError("mock must be a bool")


@dataclass(frozen=True, slots=True)
class ExperimentMetadata(SerializableContract):
    """Unresolved experiment fields pending real data and evaluation."""

    experiment_id: str | None
    task: str | None
    dataset_version: str | None
    feature_set: str | None

    def __post_init__(self) -> None:
        _require_optional_text(self.experiment_id, "experiment_id")
        _require_optional_text(self.task, "task")
        _require_optional_text(self.dataset_version, "dataset_version")
        _require_optional_text(self.feature_set, "feature_set")


@dataclass(frozen=True, slots=True)
class AnalysisStageResult(SerializableContract):
    """Common pending-only shape for an R1 analysis stage."""

    status: AnalysisStatus
    message: str
    model: ModelMetadata | None = None
    experiment: ExperimentMetadata | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, AnalysisStatus):
            raise TypeError("status must be an AnalysisStatus")
        _require_text(self.message, "message")
        if self.model is not None and not isinstance(self.model, ModelMetadata):
            raise TypeError("model must be ModelMetadata or None")
        if self.experiment is not None and not isinstance(self.experiment, ExperimentMetadata):
            raise TypeError("experiment must be ExperimentMetadata or None")


@dataclass(frozen=True, slots=True)
class SurvivalPredictionResult(AnalysisStageResult):
    """Pending survival-prediction contract with no invented estimate."""


@dataclass(frozen=True, slots=True)
class SurvivalEvaluationResult(AnalysisStageResult):
    """Pending censoring-aware evaluation contract with no invented metric."""


@dataclass(frozen=True, slots=True)
class SubtypePredictionResult(AnalysisStageResult):
    """Pending subtype contract that deliberately freezes no label taxonomy."""


@dataclass(frozen=True, slots=True)
class SubtypeEvaluationResult(AnalysisStageResult):
    """Pending multi-class evaluation contract with no invented metric."""


@dataclass(frozen=True, slots=True)
class FeatureImportanceResult(AnalysisStageResult):
    """Pending gene-importance contract with no model-derived ranking."""


@dataclass(frozen=True, slots=True)
class AnalysisResult(SerializableContract):
    """Aggregate R1 state shared independently of Streamlit."""

    validation: DatasetValidationReport
    cohort: CohortSummary
    survival_prediction: SurvivalPredictionResult
    survival_evaluation: SurvivalEvaluationResult
    subtype_prediction: SubtypePredictionResult
    subtype_evaluation: SubtypeEvaluationResult
    feature_importance: FeatureImportanceResult

    def __post_init__(self) -> None:
        expected = (
            (self.validation, DatasetValidationReport, "validation"),
            (self.cohort, CohortSummary, "cohort"),
            (self.survival_prediction, SurvivalPredictionResult, "survival_prediction"),
            (self.survival_evaluation, SurvivalEvaluationResult, "survival_evaluation"),
            (self.subtype_prediction, SubtypePredictionResult, "subtype_prediction"),
            (self.subtype_evaluation, SubtypeEvaluationResult, "subtype_evaluation"),
            (self.feature_importance, FeatureImportanceResult, "feature_importance"),
        )
        for value, contract_type, field_name in expected:
            if not isinstance(value, contract_type):
                raise TypeError(f"{field_name} must be {contract_type.__name__}")
