"""Canonical, read-only R4 preprocessing integration tests."""

from __future__ import annotations

import hashlib
from pathlib import Path

from src.contracts import PreprocessingTask
from src.data.metabric import MetabricPaths
from src.preprocessing.metabric import verify_canonical_preprocessing


ROOT = Path(__file__).resolve().parents[1]


def test_canonical_preprocessing_report_is_leak_safe_and_read_only() -> None:
    """Changing task counts, features, fit boundaries, or canonical bytes must fail the R4 gate."""
    paths = MetabricPaths.from_repository_root(ROOT)
    raw_before = hashlib.sha256(paths.raw_csv.read_bytes()).hexdigest()
    prepared_before = hashlib.sha256(paths.prepared_csv.read_bytes()).hexdigest()

    report = verify_canonical_preprocessing(paths)
    tasks = {metadata.task: metadata for metadata in report.tasks}

    assert tasks[PreprocessingTask.CLINICAL_SURVIVAL].eligible_row_count == 1903
    assert tasks[PreprocessingTask.CLINICAL_MRNA_SURVIVAL].eligible_row_count == 1903
    assert tasks[PreprocessingTask.SUBTYPE_CLASSIFICATION].eligible_row_count == 1898
    assert tasks[PreprocessingTask.CLINICAL_SURVIVAL].transformed_feature_count == 16
    assert tasks[PreprocessingTask.CLINICAL_MRNA_SURVIVAL].transformed_feature_count == 505
    assert tasks[PreprocessingTask.SUBTYPE_CLASSIFICATION].transformed_feature_count == 489
    assert tasks[PreprocessingTask.CLINICAL_MRNA_SURVIVAL].mrna_feature_names[:3] == (
        "brca1",
        "brca2",
        "palb2",
    )
    assert tasks[PreprocessingTask.CLINICAL_MRNA_SURVIVAL].mrna_feature_names[-3:] == (
        "ugt2b15",
        "ugt2b17",
        "ugt2b7",
    )
    assert report.tumor_size_missing_indicator_count == 20
    assert report.er_ihc_missing_indicator_count == 30
    assert report.mutation_feature_count == 0
    assert report.forbidden_feature_count == 0
    assert report.train_only_fit_verified is True
    assert report.canonical_artifacts_unchanged is True
    assert report.raw_sha256 == raw_before == hashlib.sha256(paths.raw_csv.read_bytes()).hexdigest()
    assert report.prepared_sha256 == prepared_before == hashlib.sha256(paths.prepared_csv.read_bytes()).hexdigest()


def test_canonical_task_split_counts_preserve_locked_manifest() -> None:
    """Reassignment or global filtering would change the task-specific locked-split counts."""
    report = verify_canonical_preprocessing(MetabricPaths.from_repository_root(ROOT))
    tasks = {metadata.task: metadata for metadata in report.tasks}

    assert [(item.split, item.eligible_count, item.excluded_count) for item in tasks[PreprocessingTask.CLINICAL_SURVIVAL].split_counts] == [
        ("train", 1332, 0),
        ("validation", 285, 1),
        ("test", 286, 0),
    ]
    assert [(item.split, item.eligible_count, item.excluded_count) for item in tasks[PreprocessingTask.SUBTYPE_CLASSIFICATION].split_counts] == [
        ("train", 1330, 2),
        ("validation", 285, 1),
        ("test", 283, 3),
    ]
