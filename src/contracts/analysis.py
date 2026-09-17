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
