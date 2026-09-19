from __future__ import annotations

from pathlib import Path
import importlib.util
import inspect
import subprocess
import sys
from types import SimpleNamespace

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
ANALYSIS_SCRIPT = ROOT / "scripts/analyze_prognostic_features.py"


def _load_analysis_module():
    spec = importlib.util.spec_from_file_location("r8_analysis_cli", ANALYSIS_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def test_analysis_cli_help_runs_from_repository_root() -> None:
    result = subprocess.run(
        [sys.executable, str(ANALYSIS_SCRIPT), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "--analysis-id" in result.stdout
    assert "--source-bundle" in result.stdout
    assert "--output-root" in result.stdout


@pytest.mark.parametrize("analysis_id", ("R8", "r8/bad", "r8\\bad", "..", "../bad"))
def test_analysis_id_rejects_uppercase_path_separators_and_parent_segments(analysis_id) -> None:
    result = subprocess.run(
        [sys.executable, str(ANALYSIS_SCRIPT), "--analysis-id", analysis_id],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "analysis ID" in result.stderr


def test_analysis_cli_enforces_canonical_r6_source(tmp_path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ANALYSIS_SCRIPT),
            "--source-bundle",
            str(tmp_path),
            "--output-root",
            str(tmp_path / "out"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "canonical R6 bundle" in result.stderr


def test_analysis_cli_refuses_existing_bundle(tmp_path) -> None:
    existing = tmp_path / "r8-prognostic-features-v1"
    existing.mkdir()
    result = subprocess.run(
        [sys.executable, str(ANALYSIS_SCRIPT), "--output-root", str(tmp_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "already exists" in result.stderr


def test_analysis_cli_calls_verify_map_extract_write_in_order_without_fitting(
    tmp_path, monkeypatch
) -> None:
    module = _load_analysis_module()
    calls: list[str] = []
    source = SimpleNamespace(feature_contract={}, model_feature_names=())
    result = SimpleNamespace(
        analysis_id="r8-test",
        effects=(SimpleNamespace(is_active=True), SimpleNamespace(is_active=False)),
    )
    mapping = ("mapping",)
    monkeypatch.setattr(module, "verify_and_load_track_b_source", lambda *args: calls.append("verify") or source)
    monkeypatch.setattr(module, "build_genomic_feature_mapping", lambda *args: calls.append("map") or mapping)
    monkeypatch.setattr(module, "validate_genomic_mapping_authorities", lambda *args: None)
    monkeypatch.setattr(module, "extract_prognostic_feature_effects", lambda *args: calls.append("extract") or result)
    monkeypatch.setattr(
        module,
        "write_prognostic_feature_bundle",
        lambda *args: calls.append("write") or (tmp_path / "bundle"),
    )
    status = module.run_analysis(
        analysis_id="r8-test",
        source_bundle=ROOT / "artifacts/models/track_b/r6-track-b-v1",
        output_root=tmp_path,
    )
    assert status["total"] == 2
    assert calls == ["verify", "map", "extract", "write"]


def test_analysis_cli_never_imports_training_or_patient_data_modules() -> None:
    module = _load_analysis_module()
    text = inspect.getsource(module)
    assert "src.training" not in text
    assert "cognivex_ml" not in text
    assert "metabric_ingestion" not in text
    assert ".fit(" not in text
    assert "fit_transform" not in text
