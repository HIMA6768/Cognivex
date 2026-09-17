"""R3 behavioral tests for aggregate-only METABRIC data quality."""

from __future__ import annotations

import json
import csv
from pathlib import Path

import pytest

from src.contracts import (
    AnalysisStatus,
    CohortSplitSummary,
    CohortSummary,
    DataQualityFinding,
    DataQualityReport,
    DataQualitySeverity,
    DataQualityStatus,
    DatasetMetadata,
    DatasetValidationIssue,
    DatasetValidationReport,
    MetabricIngestionResult,
    ValidationIssueSeverity,
)
from src.data.metabric import MetabricPaths, load_metabric
from src.data.metabric_quality import evaluate_metabric_quality
from src.data.quality_rules import QualityRules
from src.ui.data_cohort_state import get_metabric_quality_state


FIELDNAMES = [
    "patient_id",
    "age_at_diagnosis",
    "tumor_size",
    "tumor_stage",
    "lymph_nodes_examined_positive",
    "er_status_measured_by_ihc",
    "pr_status",
    "her2_status",
    "mrna_a",
    "mutation_a",
    "overall_survival_months",
    "overall_survival",
    "pam50_+_claudin-low_subtype",
]


def _rows() -> list[dict[str, str]]:
    return [
        {
            "patient_id": "synthetic-1",
            "age_at_diagnosis": "55",
            "tumor_size": "20",
            "tumor_stage": "1",
            "lymph_nodes_examined_positive": "1",
            "er_status_measured_by_ihc": "Positive",
            "pr_status": "Positive",
            "her2_status": "Negative",
            "mrna_a": "0.2",
            "mutation_a": "0",
            "overall_survival_months": "12",
            "overall_survival": "1",
            "pam50_+_claudin-low_subtype": "LumA",
        },
        {
            "patient_id": "synthetic-2",
            "age_at_diagnosis": "62",
            "tumor_size": "15",
            "tumor_stage": "Unknown",
            "lymph_nodes_examined_positive": "0",
            "er_status_measured_by_ihc": "Negative",
            "pr_status": "Negative",
            "her2_status": "Positive",
            "mrna_a": "-0.1",
            "mutation_a": "1",
            "overall_survival_months": "24",
            "overall_survival": "0",
            "pam50_+_claudin-low_subtype": "LumB",
        },
        {
            "patient_id": "synthetic-3",
            "age_at_diagnosis": "48",
            "tumor_size": "11",
            "tumor_stage": "2",
            "lymph_nodes_examined_positive": "2",
            "er_status_measured_by_ihc": "Positive",
            "pr_status": "Positive",
            "her2_status": "Negative",
            "mrna_a": "0.5",
            "mutation_a": "0",
            "overall_survival_months": "36",
            "overall_survival": "1",
            "pam50_+_claudin-low_subtype": "NC",
        },
    ]


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _ready_ingestion() -> MetabricIngestionResult:
    return MetabricIngestionResult(
        validation=DatasetValidationReport(
            status=AnalysisStatus.DATA_READY,
            message="Synthetic R2 validation passed.",
        ),
        cohort=CohortSummary(
            status=AnalysisStatus.DATA_READY,
            message="Synthetic aggregate cohort is ready.",
            patient_records=3,
            matched_samples=3,
            split_summary=CohortSplitSummary(1, 1, 1),
        ),
        metadata=DatasetMetadata(
            dataset_name="Synthetic METABRIC",
            column_count=len(FIELDNAMES),
            clinical_feature_count=7,
            mrna_feature_count=1,
            mutation_feature_count=1,
            clinical_feature_names=tuple(FIELDNAMES[1:8]),
            subtype_labels=("Luminal A", "Luminal B"),
            subtype_nc_policy="NC is retained for survival and excluded only later from subtype training.",
            prepared_dataset_path=Path("data/metabric/prepared/METABRIC_prepared.csv"),
        ),
        artifacts=(),
    )


def _synthetic_paths(
    tmp_path: Path,
    *,
    rows: list[dict[str, str]] | None = None,
    mapping_rows: list[dict[str, str]] | None = None,
    manifest_rows: list[dict[str, str]] | None = None,
    feature_groups: dict[str, object] | None = None,
) -> MetabricPaths:
    paths = MetabricPaths.from_repository_root(tmp_path)
    paths.prepared_csv.parent.mkdir(parents=True)
    paths.metadata_dir.mkdir(parents=True)
    active_rows = rows or _rows()
    _write_csv(paths.prepared_csv, FIELDNAMES, active_rows)
    _write_csv(
        paths.metadata_dir / "patient_mapping.csv",
        ["patient_id", "genomic_sample_id", "mapping_rule"],
        mapping_rows
        or [
            {"patient_id": "synthetic-1", "genomic_sample_id": "sample-1", "mapping_rule": "one_to_one"},
            {"patient_id": "synthetic-2", "genomic_sample_id": "sample-2", "mapping_rule": "one_to_one"},
            {"patient_id": "synthetic-3", "genomic_sample_id": "sample-3", "mapping_rule": "one_to_one"},
        ],
    )
    _write_csv(
        paths.metadata_dir / "manifest.csv",
        ["patient_id", "data_source", "split"],
        manifest_rows
        or [
            {"patient_id": "synthetic-1", "data_source": "synthetic", "split": "train"},
            {"patient_id": "synthetic-2", "data_source": "synthetic", "split": "validation"},
            {"patient_id": "synthetic-3", "data_source": "synthetic", "split": "test"},
        ],
    )
    (paths.metadata_dir / "clinical_schema.json").write_text(
        json.dumps(
            {
                "input_features": {
                    "age_at_diagnosis": {"type": "float", "nullable": False},
                    "tumor_size": {"type": "float", "nullable": True},
                    "tumor_stage": {"type": "categorical", "nullable": False, "categories": ["1", "2", "3", "4", "Unknown"]},
                    "lymph_nodes_examined_positive": {"type": "integer", "nullable": False},
                    "er_status_measured_by_ihc": {"type": "categorical", "nullable": True, "categories": ["Positive", "Negative"]},
                    "pr_status": {"type": "categorical", "nullable": False, "categories": ["Positive", "Negative"]},
                    "her2_status": {"type": "categorical", "nullable": False, "categories": ["Positive", "Negative"]},
                },
                "survival_targets": {"time_column": "overall_survival_months", "event_column": "overall_survival"},
            }
        ),
        encoding="utf-8",
    )
    (paths.metadata_dir / "feature_groups.json").write_text(
        json.dumps(
            feature_groups
            or {
                "clinical_features": FIELDNAMES[1:8],
                "mrna_features": ["mrna_a"],
                "mutation_features": ["mutation_a"],
                "subtype_target": "pam50_+_claudin-low_subtype",
            }
        ),
        encoding="utf-8",
    )
    (paths.metadata_dir / "subtype_labels.json").write_text(
        json.dumps(
            {
                "taxonomy_column": "pam50_+_claudin-low_subtype",
                "classes": ["Luminal A", "Luminal B"],
                "mapping": {"LumA": "Luminal A", "LumB": "Luminal B"},
                "nc_policy": "NC is retained for survival and excluded only later from subtype training.",
            }
        ),
        encoding="utf-8",
    )
    return paths


def test_quality_report_serializes_aggregate_findings_without_identifiers() -> None:
    """Removing severity aggregation or leaking record data would break this contract."""
    finding = DataQualityFinding(
        code="ZERO_SURVIVAL_DURATION",
        severity=DataQualitySeverity.WARNING,
        title="Zero survival duration",
        message="One record has a zero survival duration.",
        affected_count=1,
        affected_fraction=1 / 3,
        subject="overall_survival_months",
        recommendation="Review the source value before later preprocessing.",
    )
    report = DataQualityReport(
        status=DataQualityStatus.DATA_QUALITY_READY_WITH_WARNINGS,
        findings=(finding,),
        cohort_size=3,
        error_count=0,
        warning_count=1,
        information_count=0,
    )

    decoded = json.loads(json.dumps(report.to_dict()))

    assert decoded["status"] == "DATA_QUALITY_READY_WITH_WARNINGS"
    assert decoded["warning_count"] == 1
    assert decoded["findings"][0]["code"] == "ZERO_SURVIVAL_DURATION"
    assert "patient_id" not in str(decoded)


def test_valid_synthetic_cohort_is_ready_with_aggregate_summaries(tmp_path: Path) -> None:
    """Removing the R3 scan's valid path would lose downstream engineering context."""
    report = evaluate_metabric_quality(_synthetic_paths(tmp_path), _ready_ingestion())

    assert report.status is DataQualityStatus.DATA_QUALITY_READY
    assert report.cohort_size == 3
    assert report.survival is not None
    assert report.survival.event_count == 2
    assert report.survival.censored_count == 1
    assert report.subtype is not None
    assert report.subtype.nc_count == 1
    assert [summary.patient_count for summary in report.split_summaries] == [1, 1, 1]


@pytest.mark.parametrize(
    ("field", "value", "finding_code"),
    [
        ("overall_survival", "2", "EVENT_VALUE_INVALID"),
        ("overall_survival_months", "", "SURVIVAL_TIME_MISSING"),
        ("overall_survival_months", "-1", "SURVIVAL_TIME_NEGATIVE"),
    ],
)
def test_invalid_survival_values_block_quality_readiness(
    tmp_path: Path, field: str, value: str, finding_code: str
) -> None:
    """Accepting invalid canonical survival targets would let later pipelines proceed unsafely."""
    rows = _rows()
    rows[0][field] = value

    report = evaluate_metabric_quality(_synthetic_paths(tmp_path, rows=rows), _ready_ingestion())

    assert report.status is DataQualityStatus.DATA_QUALITY_BLOCKED
    assert finding_code in {finding.code for finding in report.findings}


def test_duplicate_prepared_patient_blocks_quality_readiness(tmp_path: Path) -> None:
    """Removing duplicate detection would permit a patient to contribute twice downstream."""
    rows = _rows()
    rows[1]["patient_id"] = "synthetic-1"

    report = evaluate_metabric_quality(_synthetic_paths(tmp_path, rows=rows), _ready_ingestion())

    assert report.status is DataQualityStatus.DATA_QUALITY_BLOCKED
    assert "PATIENT_ID_DUPLICATE" in {finding.code for finding in report.findings}


def test_manifest_split_contamination_blocks_quality_readiness(tmp_path: Path) -> None:
    """Allowing the same patient in two partitions would invalidate later evaluation."""
    manifest_rows = [
        {"patient_id": "synthetic-1", "data_source": "synthetic", "split": "train"},
        {"patient_id": "synthetic-1", "data_source": "synthetic", "split": "validation"},
        {"patient_id": "synthetic-2", "data_source": "synthetic", "split": "test"},
        {"patient_id": "synthetic-3", "data_source": "synthetic", "split": "test"},
    ]

    report = evaluate_metabric_quality(
        _synthetic_paths(tmp_path, manifest_rows=manifest_rows), _ready_ingestion()
    )

    assert report.status is DataQualityStatus.DATA_QUALITY_BLOCKED
    assert "SPLIT_CONTAMINATION" in {finding.code for finding in report.findings}


def test_non_one_to_one_patient_sample_mapping_blocks_quality_readiness(tmp_path: Path) -> None:
    """Removing genomic-sample uniqueness would invalidate patient/sample joins."""
    mapping_rows = [
        {"patient_id": "synthetic-1", "genomic_sample_id": "sample-1", "mapping_rule": "one_to_one"},
        {"patient_id": "synthetic-2", "genomic_sample_id": "sample-1", "mapping_rule": "one_to_one"},
        {"patient_id": "synthetic-3", "genomic_sample_id": "sample-3", "mapping_rule": "one_to_one"},
    ]

    report = evaluate_metabric_quality(
        _synthetic_paths(tmp_path, mapping_rows=mapping_rows), _ready_ingestion()
    )

    assert report.status is DataQualityStatus.DATA_QUALITY_BLOCKED
    assert "PATIENT_MAPPING_INCONSISTENT" in {finding.code for finding in report.findings}


def test_unexpected_clinical_category_blocks_quality_readiness(tmp_path: Path) -> None:
    """Allowing values outside clinical_schema.json would break the canonical contract."""
    rows = _rows()
    rows[0]["tumor_stage"] = "9"

    report = evaluate_metabric_quality(_synthetic_paths(tmp_path, rows=rows), _ready_ingestion())

    assert report.status is DataQualityStatus.DATA_QUALITY_BLOCKED
    assert "CLINICAL_SCHEMA_VIOLATION" in {finding.code for finding in report.findings}


def test_unknown_tumor_stage_is_accepted_and_reported(tmp_path: Path) -> None:
    """Treating canonical Unknown as malformed would reject an intentional prepared category."""
    report = evaluate_metabric_quality(_synthetic_paths(tmp_path), _ready_ingestion())

    assert report.status is DataQualityStatus.DATA_QUALITY_READY
    assert "TUMOR_STAGE_UNKNOWN" in {finding.code for finding in report.findings}
    assert "CLINICAL_SCHEMA_VIOLATION" not in {finding.code for finding in report.findings}


def test_missing_declared_genomic_feature_blocks_quality_readiness(tmp_path: Path) -> None:
    """Ignoring a declared genomic column would make later feature processing ambiguous."""
    feature_groups = {
        "clinical_features": FIELDNAMES[1:8],
        "mrna_features": ["mrna_a", "mrna_missing"],
        "mutation_features": ["mutation_a"],
        "subtype_target": "pam50_+_claudin-low_subtype",
    }

    report = evaluate_metabric_quality(
        _synthetic_paths(tmp_path, feature_groups=feature_groups), _ready_ingestion()
    )

    assert report.status is DataQualityStatus.DATA_QUALITY_BLOCKED
    assert "GENOMIC_FEATURE_MISSING" in {finding.code for finding in report.findings}


@pytest.mark.parametrize(
    ("value", "finding_code"),
    [("not-a-number", "GENOMIC_VALUE_NON_NUMERIC"), ("inf", "GENOMIC_VALUE_INFINITE")],
)
def test_invalid_genomic_values_block_quality_readiness(
    tmp_path: Path, value: str, finding_code: str
) -> None:
    """Allowing non-finite feature values would break future preprocessing assumptions."""
    rows = _rows()
    rows[0]["mrna_a"] = value

    report = evaluate_metabric_quality(_synthetic_paths(tmp_path, rows=rows), _ready_ingestion())

    assert report.status is DataQualityStatus.DATA_QUALITY_BLOCKED
    assert finding_code in {finding.code for finding in report.findings}


def test_zero_variance_genomic_feature_is_a_warning_without_filtering(tmp_path: Path) -> None:
    """Dropping a constant feature in R3 would violate the report-only boundary."""
    rows = _rows()
    for row in rows:
        row["mrna_a"] = "0.2"

    report = evaluate_metabric_quality(_synthetic_paths(tmp_path, rows=rows), _ready_ingestion())

    assert report.status is DataQualityStatus.DATA_QUALITY_READY_WITH_WARNINGS
    assert "GENOMIC_ZERO_VARIANCE" in {finding.code for finding in report.findings}
    assert report.genomic_summaries[0].zero_variance_feature_count == 1


def test_mutation_annotation_values_are_not_misclassified_as_non_numeric(tmp_path: Path) -> None:
    """Treating canonical mutation annotations as numeric would falsely block the real handoff."""
    rows = _rows()
    rows[0]["mutation_a"] = "H1047R"
    rows[1]["mutation_a"] = "0"
    rows[2]["mutation_a"] = "R175H"

    report = evaluate_metabric_quality(_synthetic_paths(tmp_path, rows=rows), _ready_ingestion())

    assert report.status is DataQualityStatus.DATA_QUALITY_READY
    assert "GENOMIC_VALUE_NON_NUMERIC" not in {finding.code for finding in report.findings}
    assert report.genomic_summaries[1].zero_variance_feature_count == 0


def test_declared_subtype_mapping_and_nc_policy_are_reported(tmp_path: Path) -> None:
    """Dropping NC or mapping raw subtype labels incorrectly would distort later track eligibility."""
    report = evaluate_metabric_quality(_synthetic_paths(tmp_path), _ready_ingestion())

    assert report.subtype is not None
    assert [count.label for count in report.subtype.class_counts] == ["Luminal A", "Luminal B"]
    assert [count.count for count in report.subtype.class_counts] == [1, 1]
    assert report.subtype.nc_count == 1
    assert "SUBTYPE_NC_POLICY" in {finding.code for finding in report.findings}


def test_unexpected_subtype_blocks_quality_readiness(tmp_path: Path) -> None:
    """An undeclared subtype must not silently enter a future classifier cohort."""
    rows = _rows()
    rows[0]["pam50_+_claudin-low_subtype"] = "Unexpected label"

    report = evaluate_metabric_quality(_synthetic_paths(tmp_path, rows=rows), _ready_ingestion())

    assert report.status is DataQualityStatus.DATA_QUALITY_BLOCKED
    assert "SUBTYPE_VALUE_UNEXPECTED" in {finding.code for finding in report.findings}


def test_nullable_clinical_missingness_produces_warning_only_report(tmp_path: Path) -> None:
    """Nullable clinical missingness needs R4 handling but must not be presented as a structural error."""
    rows = _rows()
    rows[0]["tumor_size"] = ""

    report = evaluate_metabric_quality(_synthetic_paths(tmp_path, rows=rows), _ready_ingestion())

    assert report.status is DataQualityStatus.DATA_QUALITY_READY_WITH_WARNINGS
    assert "CLINICAL_VALUE_MISSING" in {finding.code for finding in report.findings}


def test_quality_scan_is_deterministic_and_exposes_no_record_payload(tmp_path: Path) -> None:
    """Caching and UI rendering require stable aggregate outputs, never source records."""
    paths = _synthetic_paths(tmp_path)

    first = evaluate_metabric_quality(paths, _ready_ingestion())
    second = evaluate_metabric_quality(paths, _ready_ingestion())

    assert first.to_dict() == second.to_dict()
    assert "synthetic-1" not in str(first.to_dict())


def test_r3_blocks_before_reading_quality_artifacts_when_r2_is_not_ready() -> None:
    """Bypassing R2 integrity would let R3 treat an untrusted cohort as usable."""
    ingestion = MetabricIngestionResult(
        validation=DatasetValidationReport(
            status=AnalysisStatus.DATA_INVALID,
            message="R2 found a structural issue.",
            issues=(
                DatasetValidationIssue(
                    code="CHECKSUM_MISMATCH",
                    severity=ValidationIssueSeverity.ERROR,
                    message="A canonical artifact checksum does not match.",
                ),
            ),
        ),
        cohort=CohortSummary(
            status=AnalysisStatus.DATA_INVALID,
            message="Aggregate cohort unavailable.",
        ),
        metadata=None,
        artifacts=(),
    )

    report = evaluate_metabric_quality(ingestion=ingestion)

    assert report.status is DataQualityStatus.DATA_QUALITY_BLOCKED
    assert [finding.code for finding in report.findings] == ["R2_CHECKSUM_MISMATCH"]


def test_centralized_duration_rule_is_an_information_only_engineering_sentinel(tmp_path: Path) -> None:
    """Turning the duration sentinel into a rejection would overstate an engineering heuristic."""
    report = evaluate_metabric_quality(
        _synthetic_paths(tmp_path), _ready_ingestion(), QualityRules(suspicious_survival_months=10)
    )

    suspicious = next(finding for finding in report.findings if finding.code == "SURVIVAL_TIME_SUSPICIOUS")
    assert suspicious.severity is DataQualitySeverity.INFORMATION
    assert report.status is DataQualityStatus.DATA_QUALITY_READY


def test_quality_session_state_reuses_aggregate_report_until_refresh() -> None:
    """Recomputing a full quality scan on every unrelated rerun would regress the R3 cache boundary."""
    state: dict[str, object] = {}
    ingestion = load_metabric()

    first = get_metabric_quality_state(state, ingestion)
    second = get_metabric_quality_state(state, ingestion)
    refreshed = get_metabric_quality_state(state, ingestion, refresh=True)

    assert first is second
    assert refreshed is not first
    assert "patient_id" not in str(refreshed.to_dict())
