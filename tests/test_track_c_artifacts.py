from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from r7_helpers import ROOT, make_synthetic_track_c_run
from src.artifacts.track_c import (
    verify_track_c_bundle,
    verify_track_c_checksums,
    verify_track_c_reload,
    write_track_c_artifacts,
)


REQUIRED = {
    "pipeline.pkl",
    "validation_leaderboard.csv",
    "metrics.json",
    "metadata.json",
    "feature_contract.json",
    "confusion_matrix.csv",
    "classification_report.json",
    "report.md",
    "checksums.sha256",
}


@pytest.fixture(scope="module")
def synthetic_run():
    return make_synthetic_track_c_run()


def test_track_c_bundle_contains_required_aggregate_files_and_ignored_pipeline(
    tmp_path: Path, synthetic_run
) -> None:
    prepared, selection, result = synthetic_run
    bundle = write_track_c_artifacts(selection, result, prepared, tmp_path)

    assert {path.name for path in bundle.iterdir()} == REQUIRED
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", str(ROOT / "artifacts/models/track_c/r7-track-c-v1/pipeline.pkl")],
        cwd=ROOT,
        check=False,
    )
    assert ignored.returncode == 0


def test_track_c_bundle_refuses_to_overwrite_existing_experiment(tmp_path: Path, synthetic_run) -> None:
    prepared, selection, result = synthetic_run
    write_track_c_artifacts(selection, result, prepared, tmp_path)

    with pytest.raises(FileExistsError, match="already exists"):
        write_track_c_artifacts(selection, result, prepared, tmp_path)


def test_metadata_contains_dataset_counts_exclusions_features_candidates_metrics_and_seeds(
    tmp_path: Path, synthetic_run
) -> None:
    prepared, selection, result = synthetic_run
    bundle = write_track_c_artifacts(selection, result, prepared, tmp_path)
    metadata = json.loads((bundle / "metadata.json").read_text(encoding="utf-8"))
    contract = json.loads((bundle / "feature_contract.json").read_text(encoding="utf-8"))

    assert metadata["track"] == "C"
    assert metadata["dataset"]["prepared_sha256"] == "a" * 64
    assert metadata["cohorts"]["train"]["eligible_rows"] == 36
    assert metadata["cohorts"]["test"]["exclusions"]["nc"] == 0
    assert metadata["selection"]["primary_metric"] == "validation_macro_f1"
    assert metadata["selection"]["candidate_test_evaluation_count"] == 0
    assert metadata["selection"]["winner_test_evaluation_count"] == 1
    assert metadata["random_states"] == {"logistic_regression": 42}
    assert metadata["feature_contract"]["expression_features"] == list(result.feature_contract.expression_features)
    assert metadata["feature_contract"]["mutation_features"] == list(result.feature_contract.mutation_features)
    assert metadata["feature_contract"]["raw_feature_order"] == list(result.feature_contract.raw_features)
    assert metadata["metrics"]["validation"]["macro_f1"] == result.validation_metrics.macro_f1
    assert metadata["metrics"]["test"]["macro_f1"] == result.test_metrics.macro_f1
    assert metadata["runtime"]["python_version"]
    assert metadata["runtime"]["pandas_version"]
    assert metadata["runtime"]["numpy_version"]
    assert metadata["runtime"]["sklearn_version"]
    assert metadata["runtime"]["git_commit"]
    assert contract["expression_feature_count"] == 50
    assert contract["mutation_feature_count"] == 18
    assert contract["raw_feature_count"] == 68
    assert contract["clinical_feature_count"] == 0


def test_reload_reproduces_predictions_ordered_probabilities_metrics_and_confusion(
    tmp_path: Path, synthetic_run
) -> None:
    prepared, selection, result = synthetic_run
    bundle = write_track_c_artifacts(selection, result, prepared, tmp_path)

    verification = verify_track_c_reload(bundle, prepared.test)

    assert verification.passed is True
    assert verification.prediction_digest_matches is True
    assert verification.probability_digest_matches is True
    assert verification.metrics_match is True
    assert verification.confusion_matrix_matches is True
    assert verification.feature_order_matches is True
    assert verification.class_order_matches is True


def test_checksums_cover_every_bundle_file_except_checksums_itself(tmp_path: Path, synthetic_run) -> None:
    prepared, selection, result = synthetic_run
    bundle = write_track_c_artifacts(selection, result, prepared, tmp_path)
    covered = {
        line.split(maxsplit=1)[1]
        for line in (bundle / "checksums.sha256").read_text(encoding="utf-8").splitlines()
    }

    assert covered == REQUIRED - {"checksums.sha256"}
    assert verify_track_c_checksums(bundle) is True


def test_bundle_contains_no_patient_ids_or_row_level_outputs(tmp_path: Path, synthetic_run) -> None:
    prepared, selection, result = synthetic_run
    bundle = write_track_c_artifacts(selection, result, prepared, tmp_path)

    for path in bundle.iterdir():
        if path.suffix in {".json", ".csv", ".md", ".sha256"}:
            text = path.read_text(encoding="utf-8").lower()
            assert "train-0" not in text
            assert "validation-0" not in text
            assert "test-0" not in text
            assert "patient_id" not in text


def test_read_only_verifier_checks_complete_bundle_without_modifying_files(
    tmp_path: Path, synthetic_run
) -> None:
    prepared, selection, result = synthetic_run
    bundle = write_track_c_artifacts(selection, result, prepared, tmp_path)
    before = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in bundle.iterdir()}

    verification = verify_track_c_bundle(bundle, prepared.test)

    after = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in bundle.iterdir()}
    assert verification.passed is True
    assert all(verification.checks.values())
    assert after == before


def test_read_only_verifier_cli_help_runs_from_repository_root() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/verify_track_c_artifacts.py", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "--bundle" in completed.stdout
