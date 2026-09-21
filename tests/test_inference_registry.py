from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from src.artifacts.inference_registry import build_canonical_registry
from src.contracts import AnalysisTrack


ROOT = Path(__file__).resolve().parents[1]


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
