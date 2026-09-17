"""R2 behavioral tests for canonical METABRIC ingestion."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
from pathlib import Path
import shutil

import pandas as pd

from src.contracts import AnalysisStatus
from src.data.metabric import MetabricPaths, load_metabric
from src.ui.data_cohort_state import get_metabric_ingestion_state


ROOT = Path(__file__).resolve().parents[1]


def _copy_canonical_package(tmp_path: Path) -> MetabricPaths:
    target = tmp_path / "data" / "metabric"
    shutil.copytree(ROOT / "data" / "metabric", target)
    return MetabricPaths.from_repository_root(tmp_path)


def _replace_checksum(paths: MetabricPaths, source_name: str, path: Path) -> None:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    checksum_path = paths.checksum_file
    lines = checksum_path.read_text(encoding="utf-8").splitlines()
    checksum_path.write_text(
        "\n".join(
            f"{digest}  {source_name}" if line.endswith(f"  {source_name}") else line
            for line in lines
        )
        + "\n",
        encoding="utf-8",
    )


def _rewrite_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open(newline="", encoding="utf-8") as stream:
        fieldnames = csv.DictReader(stream).fieldnames
    assert fieldnames is not None
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _load_prepare_module():
    script_path = ROOT / "scripts" / "prepare_data.py"
    spec = importlib.util.spec_from_file_location("r2_prepare_data", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_load_metabric_returns_only_validated_aggregate_contracts() -> None:
    """Removing integrity validation or leaking source rows must fail this test."""
    paths = MetabricPaths.from_repository_root(ROOT)

    result = load_metabric(paths)

    assert result.validation.status is AnalysisStatus.DATA_READY
    assert result.cohort.patient_records == 1904
    assert result.cohort.matched_samples == 1904
    assert result.cohort.split_summary.train_patients == 1332
    assert result.cohort.split_summary.validation_patients == 286
    assert result.cohort.split_summary.test_patients == 286
    assert result.metadata.column_count == 693
    assert result.metadata.prepared_dataset_path == Path("data/metabric/prepared/METABRIC_prepared.csv")
    assert not hasattr(result, "rows")


def test_checksum_mismatch_marks_data_invalid(tmp_path: Path) -> None:
    """Bypassing immutable-artifact integrity checks must invalidate ingestion."""
    paths = _copy_canonical_package(tmp_path)
    paths.prepared_csv.write_text("tampered", encoding="utf-8")

    result = load_metabric(paths)

    assert result.validation.status is AnalysisStatus.DATA_INVALID
    assert "CHECKSUM_MISMATCH" in {issue.code for issue in result.validation.issues}


def test_missing_canonical_artifact_marks_data_invalid(tmp_path: Path) -> None:
    """Removing a required canonical file must not produce a trusted cohort."""
    paths = _copy_canonical_package(tmp_path)
    paths.metadata_dir.joinpath("manifest.csv").unlink()

    result = load_metabric(paths)

    assert result.validation.status is AnalysisStatus.DATA_INVALID
    assert "ARTIFACT_MISSING" in {issue.code for issue in result.validation.issues}


def test_invalid_metadata_marks_data_invalid(tmp_path: Path) -> None:
    """Malformed metadata must not be silently treated as an empty schema."""
    paths = _copy_canonical_package(tmp_path)
    schema_path = paths.metadata_dir / "clinical_schema.json"
    schema_path.write_text("{not json", encoding="utf-8")
    _replace_checksum(paths, "clinical_schema.json", schema_path)

    result = load_metabric(paths)

    assert result.validation.status is AnalysisStatus.DATA_INVALID
    assert "METADATA_INVALID" in {issue.code for issue in result.validation.issues}


def test_missing_required_prepared_column_marks_data_invalid(tmp_path: Path) -> None:
    """A prepared schema missing a declared clinical field must be rejected."""
    paths = _copy_canonical_package(tmp_path)
    with paths.prepared_csv.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        row.pop("tumor_size")
    with paths.prepared_csv.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=[key for key in rows[0] if key != "tumor_size"])
        writer.writeheader()
        writer.writerows(rows)
    _replace_checksum(paths, "METABRIC_prepared.csv", paths.prepared_csv)

    result = load_metabric(paths)

    assert result.validation.status is AnalysisStatus.DATA_INVALID
    assert "SCHEMA_MISMATCH" in {issue.code for issue in result.validation.issues}


def test_duplicate_prepared_patient_id_marks_data_invalid(tmp_path: Path) -> None:
    """A duplicate patient key must prevent a false one-patient-per-row cohort."""
    paths = _copy_canonical_package(tmp_path)
    with paths.prepared_csv.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    rows[1]["patient_id"] = rows[0]["patient_id"]
    _rewrite_csv(paths.prepared_csv, rows)
    _replace_checksum(paths, "METABRIC_prepared.csv", paths.prepared_csv)

    result = load_metabric(paths)

    assert result.validation.status is AnalysisStatus.DATA_INVALID
    assert "DUPLICATE_PATIENT_ID" in {issue.code for issue in result.validation.issues}


def test_non_one_to_one_patient_mapping_marks_data_invalid(tmp_path: Path) -> None:
    """Duplicate genomic mappings must not be accepted as matched samples."""
    paths = _copy_canonical_package(tmp_path)
    mapping_path = paths.metadata_dir / "patient_mapping.csv"
    with mapping_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    rows[1]["genomic_sample_id"] = rows[0]["genomic_sample_id"]
    _rewrite_csv(mapping_path, rows)
    _replace_checksum(paths, "patient_mapping.csv", mapping_path)

    result = load_metabric(paths)

    assert result.validation.status is AnalysisStatus.DATA_INVALID
    assert "PATIENT_MAPPING_INVALID" in {issue.code for issue in result.validation.issues}


def test_unknown_manifest_split_marks_data_invalid(tmp_path: Path) -> None:
    """An unrecognized locked-partition label must stop cohort readiness."""
    paths = _copy_canonical_package(tmp_path)
    manifest_path = paths.metadata_dir / "manifest.csv"
    with manifest_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    rows[0]["split"] = "holdout"
    _rewrite_csv(manifest_path, rows)
    _replace_checksum(paths, "manifest.csv", manifest_path)

    result = load_metabric(paths)

    assert result.validation.status is AnalysisStatus.DATA_INVALID
    assert "MANIFEST_INVALID" in {issue.code for issue in result.validation.issues}


def test_preparation_reproduces_canonical_prepared_semantics_without_mutating_raw(tmp_path: Path) -> None:
    """Changing a documented preparation transform or writing raw data must fail this test."""
    prepare_data = _load_prepare_module()
    raw_path = ROOT / "data" / "metabric" / "raw" / "METABRIC_RNA_Mutation.csv"
    prepared_path = ROOT / "data" / "metabric" / "prepared" / "METABRIC_prepared.csv"
    raw_checksum_before = hashlib.sha256(raw_path.read_bytes()).hexdigest()

    prepare_data.prepare_dataset(raw_path, tmp_path)

    reproduced = pd.read_csv(tmp_path / "prepared" / "METABRIC_prepared.csv", low_memory=False)
    canonical = pd.read_csv(prepared_path, low_memory=False)
    pd.testing.assert_frame_equal(reproduced, canonical)
    pd.testing.assert_frame_equal(
        pd.read_csv(tmp_path / "metadata" / "patient_mapping.csv"),
        pd.read_csv(ROOT / "data" / "metabric" / "metadata" / "patient_mapping.csv"),
    )
    pd.testing.assert_frame_equal(
        pd.read_csv(tmp_path / "metadata" / "manifest.csv"),
        pd.read_csv(ROOT / "data" / "metabric" / "metadata" / "manifest.csv"),
    )
    assert hashlib.sha256(raw_path.read_bytes()).hexdigest() == raw_checksum_before


def test_session_state_reuses_aggregate_result_until_explicit_refresh() -> None:
    """Dropping the cache or retaining source rows in session state must fail this test."""
    session_state: dict[str, object] = {}

    first = get_metabric_ingestion_state(session_state)
    second = get_metabric_ingestion_state(session_state)
    refreshed = get_metabric_ingestion_state(session_state, refresh=True)

    assert first is second
    assert refreshed is not first
    assert refreshed.validation.status is AnalysisStatus.DATA_READY
    assert all(not isinstance(value, list) for value in session_state.values())
