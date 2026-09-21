from __future__ import annotations

import json
import logging
from pathlib import Path
import subprocess
import sys

import pytest

from src.artifacts.inference_registry import build_canonical_registry
from src.artifacts.prognostic_features import (
    R6_BUNDLE_RELATIVE,
    verify_frozen_r6_tracked_state,
    verify_r6_checksums,
)
from src.contracts import AnalysisTrack


ROOT = Path(__file__).resolve().parents[1]


def _clone_with_lf_checkout(tmp_path: Path, *, shallow: bool) -> Path:
    clone = tmp_path / ("shallow-lf-clone" if shallow else "lf-clone")
    source = ROOT.as_uri() if shallow else str(ROOT)
    command = ["git", "clone", "--quiet", "--no-checkout"]
    if shallow:
        command.append("--depth=1")
    else:
        command.extend(("--local", "--no-hardlinks"))
    subprocess.run([*command, source, str(clone)], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(clone), "config", "core.autocrlf", "false"], check=True)
    subprocess.run(["git", "-C", str(clone), "config", "core.eol", "lf"], check=True)
    subprocess.run(["git", "-C", str(clone), "checkout", "--quiet", "HEAD"], check=True)
    return clone


def test_registry_loads_verified_canonical_contracts_once() -> None:
    registry = build_canonical_registry(ROOT)
    assert registry.global_contract.raw_fields == registry.track_b.required_fields
    assert len(registry.global_contract.raw_fields) == 75
    assert registry.track_a.available
    assert registry.track_b.available
    assert registry.track_c.available
    assert registry.r8.available


def test_registry_has_exact_track_contract_counts() -> None:
    registry = build_canonical_registry(ROOT)
    assert len(registry.entry(AnalysisTrack.TRACK_A).required_fields) == 7
    assert len(registry.entry(AnalysisTrack.TRACK_B).required_fields) == 75
    assert len(registry.entry(AnalysisTrack.TRACK_C).required_fields) == 68


def test_failed_track_initialization_is_isolated(monkeypatch) -> None:
    import src.artifacts.inference_registry as registry_module

    def fail_r6(_root):
        raise ValueError("post-load failure")

    monkeypatch.setattr(registry_module, "_r6", fail_r6)
    registry = registry_module.build_canonical_registry(ROOT)

    assert registry.track_a.available
    assert not registry.track_b.available
    assert registry.track_b.error_code == "ARTIFACT_UNAVAILABLE"
    assert registry.track_c.available
    assert registry.r8.available


@pytest.mark.parametrize(
    ("track", "loader_name"),
    (
        (AnalysisTrack.TRACK_A, "_r5"),
        (AnalysisTrack.TRACK_B, "_r6"),
        (AnalysisTrack.TRACK_C, "_r7"),
    ),
)
def test_registry_logs_safe_per_track_runtime_state_on_loader_failure(
    monkeypatch, caplog, track: AnalysisTrack, loader_name: str
) -> None:
    """Masked loader failures must retain safe server-side diagnostic evidence."""
    import src.artifacts.inference_registry as registry_module

    def fail_loader(_root: Path):
        raise RuntimeError(f"simulated {track.value} loader failure")

    monkeypatch.setattr(registry_module, loader_name, fail_loader)

    with caplog.at_level(logging.ERROR, logger="src.artifacts.inference_registry"):
        registry = registry_module.build_canonical_registry(ROOT)

    assert not registry.entry(track).available
    assert "[ONCOMAP_TRACK_LOAD_ERROR]" in caplog.text
    assert f"track={track.value.removeprefix('track_').upper()}" in caplog.text
    assert "exception_class=RuntimeError" in caplog.text
    assert f"simulated {track.value} loader failure" in caplog.text
    assert "Traceback" in caplog.text
    assert "checksum_verification" in caplog.text
    if track is AnalysisTrack.TRACK_C:
        assert "pipeline.pkl" in caplog.text
    else:
        assert "preprocessor.pkl" in caplog.text
        assert "cox_model.pkl" in caplog.text


def test_clean_clone_builds_the_exact_global_contract_without_local_handoff_metadata(tmp_path: Path) -> None:
    """Deployment must load solely from committed canonical data and artifacts."""
    clean_root = tmp_path / "clean-clone"
    subprocess.run(
        [
            "git",
            "clone",
            "--quiet",
            "--local",
            "--no-hardlinks",
            str(ROOT),
            str(clean_root),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    handoff_files = tuple(
        path.relative_to(clean_root).as_posix()
        for path in (clean_root / "ai_handoff_data").rglob("*")
        if path.is_file()
    )
    assert handoff_files == ("ai_handoff_data/v1/selected_features.txt",)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json; from pathlib import Path; "
                "from src.artifacts.inference_registry import build_canonical_registry; "
                "root = Path('.').resolve(); registry = build_canonical_registry(root); "
                "print(json.dumps(list(registry.global_contract.raw_fields)))"
            ),
        ],
        cwd=clean_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    raw_features = tuple(json.loads(result.stdout))
    contract = json.loads(
        (clean_root / "artifacts/models/track_b/r6-track-b-v1/feature_contract.json").read_text(
            encoding="utf-8"
        )
    )
    assert contract["clinical_feature_count"] == 7
    assert contract["expression_feature_count"] == 50
    assert contract["mutation_feature_count"] == 18
    assert raw_features == tuple(contract["raw_feature_names"])
    assert raw_features == tuple(
        contract["clinical_features"]
        + contract["expression_features"]
        + contract["mutation_features"]
    )
    assert len(raw_features) == 75


@pytest.mark.parametrize("shallow", (False, True))
def test_lf_only_tracked_checkout_builds_the_canonical_registry(tmp_path: Path, shallow: bool) -> None:
    """Canonical trust verification must be independent of checkout line endings/history depth."""
    clean_root = _clone_with_lf_checkout(tmp_path, shallow=shallow)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from pathlib import Path; "
                "from src.artifacts.inference_registry import build_canonical_registry; "
                "registry = build_canonical_registry(Path('.')); "
                "assert registry.track_a.available and registry.track_b.available and registry.track_c.available; "
                "assert len(registry.global_contract.raw_fields) == 75"
            ),
        ],
        cwd=clean_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_r6_checksum_verification_rejects_one_protected_binary_byte_in_lf_checkout(tmp_path: Path) -> None:
    clean_root = _clone_with_lf_checkout(tmp_path, shallow=False)
    bundle = clean_root / R6_BUNDLE_RELATIVE
    model = bundle / "cox_model.pkl"
    model.write_bytes(model.read_bytes() + b"tamper")

    with pytest.raises(ValueError, match="checksum verification failed for cox_model.pkl"):
        verify_r6_checksums(bundle)


def test_r6_checksum_verification_rejects_an_unexpected_model_binary(tmp_path: Path) -> None:
    clean_root = _clone_with_lf_checkout(tmp_path, shallow=False)
    bundle = clean_root / R6_BUNDLE_RELATIVE
    unexpected = bundle / "unapproved_model.pkl"
    unexpected.write_bytes(b"not a trusted model")
    subprocess.run(["git", "-C", str(clean_root), "add", str(unexpected)], check=True)

    with pytest.raises(ValueError, match="unexpected file"):
        verify_r6_checksums(bundle)


def test_r6_frozen_source_drift_is_rejected_when_frozen_commit_is_available(tmp_path: Path) -> None:
    clean_root = _clone_with_lf_checkout(tmp_path, shallow=False)
    source = clean_root / "src/training/track_b.py"
    source.write_text(source.read_text(encoding="utf-8") + "\n# test-only source drift\n", encoding="utf-8")

    with pytest.raises(ValueError, match="frozen R6 tracked files differ"):
        verify_frozen_r6_tracked_state(clean_root)
