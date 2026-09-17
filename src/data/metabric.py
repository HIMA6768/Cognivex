"""Aggregate-only ingestion for the canonical repository METABRIC handoff."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.contracts import (
    AnalysisStatus,
    CohortSplitSummary,
    CohortSummary,
    DataArtifactStatus,
    DatasetMetadata,
    DatasetValidationIssue,
    DatasetValidationReport,
    MetabricIngestionResult,
    ValidationIssueSeverity,
)


@dataclass(frozen=True, slots=True)
class MetabricPaths:
    """Repository-relative locations of the canonical R2 handoff artifacts."""

    repository_root: Path

    @classmethod
    def from_repository_root(cls, root: Path | None = None) -> "MetabricPaths":
        return cls(root or Path(__file__).resolve().parents[2])

    @property
    def data_root(self) -> Path:
        return self.repository_root / "data" / "metabric"

    @property
    def raw_csv(self) -> Path:
        return self.data_root / "raw" / "METABRIC_RNA_Mutation.csv"

    @property
    def prepared_csv(self) -> Path:
        return self.data_root / "prepared" / "METABRIC_prepared.csv"

    @property
    def metadata_dir(self) -> Path:
        return self.data_root / "metadata"

    @property
    def checksum_file(self) -> Path:
        return self.metadata_dir / "SHA256SUMS.txt"


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _checksum_paths(paths: MetabricPaths) -> dict[str, Path]:
    return {
        "METABRIC_RNA_Mutation.csv": paths.raw_csv,
        "METABRIC_prepared.csv": paths.prepared_csv,
        "clinical_schema.json": paths.metadata_dir / "clinical_schema.json",
        "subtype_labels.json": paths.metadata_dir / "subtype_labels.json",
        "feature_groups.json": paths.metadata_dir / "feature_groups.json",
        "dataset_summary.json": paths.metadata_dir / "dataset_summary.json",
        "dataset_provenance.json": paths.metadata_dir / "dataset_provenance.json",
        "manifest.csv": paths.metadata_dir / "manifest.csv",
        "patient_mapping.csv": paths.metadata_dir / "patient_mapping.csv",
        "HANDOFF_README.md": paths.data_root / "README.md",
    }


def _required_paths(paths: MetabricPaths) -> tuple[Path, ...]:
    return (paths.checksum_file, *_checksum_paths(paths).values())


def _issue(code: str, message: str) -> DatasetValidationIssue:
    return DatasetValidationIssue(code, ValidationIssueSeverity.ERROR, message)


def _invalid_result(
    issues: tuple[DatasetValidationIssue, ...],
    artifacts: tuple[DataArtifactStatus, ...] = (),
) -> MetabricIngestionResult:
    return MetabricIngestionResult(
        validation=DatasetValidationReport(
            status=AnalysisStatus.DATA_INVALID,
            message="Canonical METABRIC data could not be validated. Review the listed data issue.",
            issues=issues,
        ),
        cohort=CohortSummary(
            status=AnalysisStatus.DATA_INVALID,
            message="Aggregate cohort information is unavailable until validation succeeds.",
        ),
        metadata=None,
        artifacts=artifacts,
    )


def _parse_checksums(paths: MetabricPaths) -> dict[str, str]:
    checksums: dict[str, str] = {}
    for line in paths.checksum_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2 or len(parts[0]) != 64:
            raise ValueError("SHA256SUMS.txt contains an invalid checksum record")
        checksums[parts[1]] = parts[0].lower()
    if not checksums:
        raise ValueError("SHA256SUMS.txt contains no checksum records")
    return checksums


def _checksum_statuses(paths: MetabricPaths, expected: dict[str, str]) -> tuple[DataArtifactStatus, ...]:
    statuses: list[DataArtifactStatus] = []
    for source_name, path in _checksum_paths(paths).items():
        statuses.append(
            DataArtifactStatus(
                source_name=source_name,
                relative_path=path.relative_to(paths.repository_root),
                checksum_verified=_sha256(path) == expected.get(source_name),
            )
        )
    return tuple(statuses)


def _csv_header_and_ids(path: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or "patient_id" not in reader.fieldnames:
            raise ValueError(f"{path.name} must include patient_id")
        return tuple(reader.fieldnames), tuple(row["patient_id"] for row in reader)


def _read_mapping(path: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        required = {"patient_id", "genomic_sample_id", "mapping_rule"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError("patient_mapping.csv must include required columns")
        rows = tuple(reader)
    return tuple(row["patient_id"] for row in rows), tuple(row["genomic_sample_id"] for row in rows)


def _read_manifest(path: Path) -> tuple[CohortSplitSummary, tuple[str, ...]]:
    allowed_splits = {"train", "validation", "test"}
    counts = {split: 0 for split in allowed_splits}
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        required = {"patient_id", "data_source", "split"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError("manifest.csv must include required columns")
        rows = tuple(reader)
    for row in rows:
        split = row["split"]
        if split not in allowed_splits:
            raise ValueError("manifest.csv includes an unsupported split")
        counts[split] += 1
    return (
        CohortSplitSummary(counts["train"], counts["validation"], counts["test"]),
        tuple(row["patient_id"] for row in rows),
    )


def _declared_columns(schema: dict[str, Any], feature_groups: dict[str, Any]) -> set[str]:
    survival_targets = schema["survival_targets"]
    columns = {
        *feature_groups["id_columns"],
        *feature_groups["clinical_features"],
        *feature_groups["other_clinical_metadata_not_in_baseline"],
        *feature_groups["mrna_features"],
        *feature_groups["mutation_features"],
        *feature_groups["survival_targets"],
        str(feature_groups["subtype_target"]),
        str(survival_targets["time_column"]),
        str(survival_targets["event_column"]),
    }
    if not all(isinstance(column, str) and column for column in columns):
        raise ValueError("Metadata declares an invalid column name")
    return columns


def _summary_split_counts(summary: dict[str, Any]) -> CohortSplitSummary:
    split_summary = summary["split_summary"]
    return CohortSplitSummary(
        int(split_summary["train"]["patients"]),
        int(split_summary["validation"]["patients"]),
        int(split_summary["test"]["patients"]),
    )


def load_metabric(paths: MetabricPaths | None = None) -> MetabricIngestionResult:
    """Load validated aggregate metadata from the canonical prepared-data handoff."""
    resolved = paths or MetabricPaths.from_repository_root()
    missing = tuple(path for path in _required_paths(resolved) if not path.is_file())
    if missing:
        return _invalid_result(
            tuple(_issue("ARTIFACT_MISSING", f"Required canonical artifact is missing: {path.name}.") for path in missing)
        )
    try:
        artifacts = _checksum_statuses(resolved, _parse_checksums(resolved))
    except (OSError, ValueError):
        return _invalid_result((_issue("METADATA_INVALID", "The checksum manifest is invalid."),))
    if not all(artifact.checksum_verified for artifact in artifacts):
        return _invalid_result(
            (_issue("CHECKSUM_MISMATCH", "A canonical artifact did not match its expected checksum."),),
            artifacts,
        )
    try:
        schema = _read_json(resolved.metadata_dir / "clinical_schema.json")
        feature_groups = _read_json(resolved.metadata_dir / "feature_groups.json")
        subtype_labels = _read_json(resolved.metadata_dir / "subtype_labels.json")
        summary = _read_json(resolved.metadata_dir / "dataset_summary.json")
    except (OSError, ValueError, json.JSONDecodeError, TypeError):
        return _invalid_result((_issue("METADATA_INVALID", "Canonical metadata could not be parsed."),), artifacts)
    try:
        prepared_header, prepared_ids = _csv_header_and_ids(resolved.prepared_csv)
        raw_header, raw_ids = _csv_header_and_ids(resolved.raw_csv)
        if prepared_header != raw_header or set(prepared_header) != _declared_columns(schema, feature_groups):
            raise ValueError("Raw, prepared, and metadata schemas differ")
        if len(prepared_ids) != len(set(prepared_ids)) or len(raw_ids) != len(set(raw_ids)):
            return _invalid_result((_issue("DUPLICATE_PATIENT_ID", "Canonical patient identifiers must be unique."),), artifacts)
        if set(prepared_ids) != set(raw_ids):
            raise ValueError("Raw and prepared patient identifiers differ")
    except (OSError, ValueError, KeyError, TypeError):
        return _invalid_result(
            (_issue("SCHEMA_MISMATCH", "Canonical data columns do not match the declared schema."),), artifacts
        )
    try:
        mapping_patient_ids, genomic_sample_ids = _read_mapping(resolved.metadata_dir / "patient_mapping.csv")
        if (
            len(mapping_patient_ids) != len(set(mapping_patient_ids))
            or len(genomic_sample_ids) != len(set(genomic_sample_ids))
            or set(mapping_patient_ids) != set(prepared_ids)
        ):
            raise ValueError("Patient mapping is not one-to-one")
    except (OSError, ValueError, KeyError):
        return _invalid_result(
            (_issue("PATIENT_MAPPING_INVALID", "Patient and genomic-sample mapping is not one-to-one."),), artifacts
        )
    try:
        split_summary, manifest_patient_ids = _read_manifest(resolved.metadata_dir / "manifest.csv")
        if len(manifest_patient_ids) != len(set(manifest_patient_ids)) or set(manifest_patient_ids) != set(prepared_ids):
            raise ValueError("Manifest patients do not match the prepared cohort")
        if split_summary != _summary_split_counts(summary):
            raise ValueError("Manifest split counts disagree with summary metadata")
    except (OSError, ValueError, KeyError, TypeError):
        return _invalid_result(
            (_issue("MANIFEST_INVALID", "The locked patient-level split manifest is invalid."),), artifacts
        )
    try:
        patient_count = len(prepared_ids)
        if patient_count != int(summary["cohort_size_patients"]):
            raise ValueError("Cohort count differs from summary")
        if len(genomic_sample_ids) != int(summary["matched_genomic_samples"]):
            raise ValueError("Matched sample count differs from summary")
        metadata = DatasetMetadata(
            dataset_name=str(summary["dataset_name"]),
            column_count=len(prepared_header),
            clinical_feature_count=len(feature_groups["clinical_features"]),
            mrna_feature_count=len(feature_groups["mrna_features"]),
            mutation_feature_count=len(feature_groups["mutation_features"]),
            clinical_feature_names=tuple(str(name) for name in feature_groups["clinical_features"]),
            subtype_labels=tuple(str(label) for label in subtype_labels["classes"]),
            subtype_nc_policy=str(subtype_labels["nc_policy"]),
            prepared_dataset_path=Path("data/metabric/prepared/METABRIC_prepared.csv"),
        )
    except (KeyError, TypeError, ValueError):
        return _invalid_result(
            (_issue("METADATA_INVALID", "Canonical aggregate metadata is incomplete."),), artifacts
        )
    cohort = CohortSummary(
        status=AnalysisStatus.DATA_READY,
        message="Canonical METABRIC cohort validated for aggregate R2 use.",
        clinical_records=patient_count,
        patient_records=patient_count,
        genomic_samples=len(genomic_sample_ids),
        matched_samples=len(genomic_sample_ids),
        split_summary=split_summary,
    )
    return MetabricIngestionResult(
        validation=DatasetValidationReport(
            status=AnalysisStatus.DATA_READY,
            message="Canonical METABRIC artifacts passed integrity and structural validation.",
        ),
        cohort=cohort,
        metadata=metadata,
        artifacts=artifacts,
    )
