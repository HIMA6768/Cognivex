"""R6 Track B persistence and trusted reload tests."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from r6_helpers import ROOT, make_single_candidate_track_b_run
from src.artifacts.track_b import verify_track_b_reload, write_track_b_artifacts


def test_track_b_bundle_contains_required_aggregate_evidence_and_ignored_pickles(
    tmp_path: Path,
) -> None:
    prepared, selection, result = make_single_candidate_track_b_run()
    bundle = write_track_b_artifacts(selection, result, prepared, tmp_path)

    assert {path.name for path in bundle.iterdir()} == {
        "metadata.json",
        "metrics.json",
        "feature_contract.json",
        "validation_leaderboard.csv",
        "report.md",
        "preprocessor.pkl",
        "cox_model.pkl",
        "checksums.sha256",
    }
    metadata = json.loads((bundle / "metadata.json").read_text(encoding="utf-8"))
    metrics = json.loads((bundle / "metrics.json").read_text(encoding="utf-8"))
    contract = json.loads((bundle / "feature_contract.json").read_text(encoding="utf-8"))
    report = (bundle / "report.md").read_text(encoding="utf-8")

    assert metadata["track"] == "B"
    assert metadata["dataset"]["prepared_sha256"] == prepared.prepared_sha256
    assert metadata["survival_contract"]["event_observed_value"] == 1
    assert metadata["selection_policy"] == "maximum validation C-index only"
    assert metadata["candidate_test_evaluation_count"] == 0
    assert metadata["winner_test_evaluation_count"] == 1
    assert contract["raw_feature_count"] == 75
    assert contract["model_feature_count"] == 80
    assert contract["model_feature_names"] == list(result.model_feature_names)
    assert metrics["track_b"]["validation"]["c_index"] == result.validation_metric.c_index
    assert metrics["comparison"]["validation_delta"] == result.validation_delta
    assert f"{result.validation_metric.c_index:.6f}" in report
    assert f"{result.test_metric.c_index:.6f}" in report
    assert "patient_id" not in json.dumps(metadata).lower()
    assert "patient_id" not in report.lower()

    for name in ("preprocessor.pkl", "cox_model.pkl"):
        completed = subprocess.run(
            [
                "git",
                "check-ignore",
                "-q",
                str(ROOT / "artifacts" / "models" / "track_b" / "example" / name),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert completed.returncode == 0, f"{name} must remain ignored"


def test_reload_reproduces_feature_order_and_risk_scores(tmp_path: Path) -> None:
    prepared, selection, result = make_single_candidate_track_b_run()
    bundle = write_track_b_artifacts(selection, result, prepared, tmp_path)

    verification = verify_track_b_reload(bundle, prepared)

    assert verification.passed is True
    assert verification.feature_order_matches is True
    assert verification.max_absolute_risk_difference <= 1e-12
    assert verification.risk_sha256 == json.loads(
        (bundle / "metadata.json").read_text(encoding="utf-8")
    )["test_risk_sha256"]


def test_track_b_bundle_refuses_overwrite(tmp_path: Path) -> None:
    prepared, selection, result = make_single_candidate_track_b_run()
    write_track_b_artifacts(selection, result, prepared, tmp_path)

    with pytest.raises(FileExistsError, match="already exists"):
        write_track_b_artifacts(selection, result, prepared, tmp_path)


def test_training_cli_runs_directly_from_repository_root() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/train_track_b.py", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "--experiment-id" in completed.stdout
    assert "--output-root" in completed.stdout
