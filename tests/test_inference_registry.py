from __future__ import annotations

from pathlib import Path

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
