from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

from src.analysis.prognostic_features import (
    build_genomic_feature_mapping,
    extract_prognostic_feature_effects,
)
from src.artifacts import prognostic_features as artifact_module
from src.artifacts.prognostic_features import (
    verify_and_load_track_b_source,
    write_prognostic_feature_bundle,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify_prognostic_feature_artifacts.py"


def test_verifier_cli_help_runs_from_repository_root() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"], cwd=ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "--bundle" in result.stdout
    assert "--source-bundle" in result.stdout


def test_verifier_cli_returns_zero_only_for_pass(tmp_path, monkeypatch) -> None:
    r6 = ROOT / "artifacts/models/track_b/r6-track-b-v1"
    source = verify_and_load_track_b_source(r6, ROOT)
    mapping = build_genomic_feature_mapping(source.feature_contract, source.model_feature_names)
    result = extract_prognostic_feature_effects(source, mapping)
    monkeypatch.setattr(artifact_module, "_utc_now", lambda: "2026-09-19T12:00:00+00:00")
    bundle = write_prognostic_feature_bundle(result, source, tmp_path)
    command = [
        sys.executable,
        str(SCRIPT),
        "--bundle",
        str(bundle),
        "--source-bundle",
        str(r6),
    ]
    passed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    assert passed.returncode == 0
    assert passed.stdout.splitlines()[0] == "PASS"
    (bundle / "report.md").write_text("tampered\n", encoding="utf-8")
    failed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    assert failed.returncode == 1
    assert failed.stdout.splitlines()[0] == "FAIL"
