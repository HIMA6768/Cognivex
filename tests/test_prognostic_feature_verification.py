from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.analysis.prognostic_features import (
    build_genomic_feature_mapping,
    extract_prognostic_feature_effects,
)
from src.artifacts import prognostic_features as artifact_module
from src.artifacts.prognostic_features import (
    verify_and_load_track_b_source,
    verify_prognostic_feature_bundle,
    write_prognostic_feature_bundle,
)


def _hash_tree(path: Path) -> dict[str, str]:
    return {
        item.name: hashlib.sha256(item.read_bytes()).hexdigest()
        for item in sorted(path.iterdir())
        if item.is_file()
    }


@pytest.fixture()
def bundle(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    r6 = root / "artifacts/models/track_b/r6-track-b-v1"
    source = verify_and_load_track_b_source(r6, root)
    mapping = build_genomic_feature_mapping(source.feature_contract, source.model_feature_names)
    result = extract_prognostic_feature_effects(source, mapping)
    monkeypatch.setattr(artifact_module, "_utc_now", lambda: "2026-09-19T12:00:00+00:00")
    monkeypatch.setattr(artifact_module, "_git_commit", lambda path: "fixed-r8-commit")
    output = write_prognostic_feature_bundle(result, source, tmp_path)
    return root, r6, output


def test_verifier_rebuilds_and_compares_all_sixty_eight_rows(bundle) -> None:
    root, r6, output = bundle
    verification = verify_prognostic_feature_bundle(output, r6, root)
    assert verification.passed is True
    assert verification.checks["effects_match"] is True


def test_verifier_checks_order_values_summary_report_lineage_and_checksums(bundle) -> None:
    root, r6, output = bundle
    checks = verify_prognostic_feature_bundle(output, r6, root).checks
    assert checks["file_set"]
    assert checks["checksums"]
    assert checks["effects_match"]
    assert checks["summary_match"]
    assert checks["report_match"]
    assert checks["lineage_match"]


def test_semantic_verification_ignores_only_declared_volatile_metadata(bundle) -> None:
    root, r6, output = bundle
    metadata_path = output / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["generated_at_utc"] = "2030-01-01T00:00:00+00:00"
    metadata["runtime"]["generation_git_commit"] = "another-valid-commit"
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifact_module.refresh_prognostic_feature_checksums(output)
    assert verify_prognostic_feature_bundle(output, r6, root).passed is True
    metadata["feature_contract"]["analyzed_total"] = 67
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifact_module.refresh_prognostic_feature_checksums(output)
    assert verify_prognostic_feature_bundle(output, r6, root).passed is False


@pytest.mark.parametrize("name", ("feature_effects.csv", "summary.json", "report.md", "metadata.json"))
def test_verifier_detects_tampered_effect_summary_report_or_lineage(bundle, name) -> None:
    root, r6, output = bundle
    path = output / name
    path.write_text(path.read_text(encoding="utf-8") + "tampered\n", encoding="utf-8")
    artifact_module.refresh_prognostic_feature_checksums(output)
    assert verify_prognostic_feature_bundle(output, r6, root).passed is False


def test_verifier_hashes_r6_and_r8_before_and_after_and_writes_nothing(bundle) -> None:
    root, r6, output = bundle
    before_r6 = _hash_tree(r6)
    before_r8 = _hash_tree(output)
    verification = verify_prognostic_feature_bundle(output, r6, root)
    assert verification.checks["source_unchanged"]
    assert verification.checks["bundle_unchanged"]
    assert _hash_tree(r6) == before_r6
    assert _hash_tree(output) == before_r8


def test_verifier_never_refreshes_checksums(bundle, monkeypatch) -> None:
    root, r6, output = bundle
    monkeypatch.setattr(
        artifact_module,
        "refresh_prognostic_feature_checksums",
        lambda path: (_ for _ in ()).throw(AssertionError("verifier attempted a write")),
    )
    assert verify_prognostic_feature_bundle(output, r6, root).passed is True
