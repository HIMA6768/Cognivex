"""Canonical, read-only R4 preprocessing integration tests."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

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
    assert tasks[PreprocessingTask.CLINICAL_MUTATION_SURVIVAL].eligible_row_count == 1903
    assert tasks[PreprocessingTask.CLINICAL_SURVIVAL].transformed_feature_count == 16
    assert tasks[PreprocessingTask.CLINICAL_MRNA_SURVIVAL].transformed_feature_count == 505
    assert tasks[PreprocessingTask.SUBTYPE_CLASSIFICATION].transformed_feature_count == 489
    assert tasks[PreprocessingTask.CLINICAL_MUTATION_SURVIVAL].transformed_feature_count == 44
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
    track_b_names = tasks[PreprocessingTask.CLINICAL_MRNA_SURVIVAL].final_feature_names
    track_d = tasks[PreprocessingTask.CLINICAL_MUTATION_SURVIVAL]
    assert not any(name.endswith("_mut_present") for name in track_b_names)
    assert report.mutation_feature_count == 27
    assert track_d.mutation_metadata is not None
    assert len(track_d.mutation_metadata.source_feature_names) == 173
    assert track_d.mutation_metadata.selection.threshold == 0.05
    assert len(track_d.mutation_metadata.selection.retained_feature_names) == 27
    assert track_d.mutation_metadata.burden_source_feature_count == 173
    assert track_d.mutation_metadata.burden_feature_name == "mutation_burden_log1p"
    assert track_d.standardized_continuous_feature_names == (
        "age_at_diagnosis",
        "tumor_size",
        "lymph_nodes_examined_positive",
        "mutation_burden_log1p",
    )
    assert len(track_d.unscaled_binary_feature_names) == 40
    assert set(track_d.standardized_continuous_feature_names).isdisjoint(
        track_d.unscaled_binary_feature_names
    )
    assert set(track_d.standardized_continuous_feature_names + track_d.unscaled_binary_feature_names) == set(
        track_d.final_feature_names
    )
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
    assert [(item.split, item.eligible_count, item.excluded_count) for item in tasks[PreprocessingTask.CLINICAL_MUTATION_SURVIVAL].split_counts] == [
        ("train", 1332, 0),
        ("validation", 285, 1),
        ("test", 286, 0),
    ]


def test_canonical_track_d_selector_matches_r4d_p0_full_training_evidence() -> None:
    """Hardcoded or globally reordered genes would diverge from independent locked-train evidence."""
    report = verify_canonical_preprocessing(MetabricPaths.from_repository_root(ROOT))
    track_d = next(
        item for item in report.tasks if item.task is PreprocessingTask.CLINICAL_MUTATION_SURVIVAL
    )
    assert track_d.mutation_metadata is not None
    profile = pd.read_csv(ROOT / "results" / "mutation_profile_train.csv")
    expected_raw_columns = tuple(
        profile.loc[profile["retain_ge_5pct"].astype(bool), "raw_column"].astype(str)
    )
    observed_raw_columns = tuple(
        item.raw_column
        for item in track_d.mutation_metadata.selection.features
        if item.retained
    )

    assert observed_raw_columns == expected_raw_columns
