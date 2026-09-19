from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from src.analysis.prognostic_features import (
    build_genomic_feature_mapping,
    extract_prognostic_feature_effects,
)
from src.artifacts import prognostic_features as artifact_module
from src.artifacts.prognostic_features import (
    refresh_prognostic_feature_checksums,
    verify_and_load_track_b_source,
    write_prognostic_feature_bundle,
)
from src.contracts import FEATURE_EFFECTS_CSV_COLUMNS


@pytest.fixture(scope="module")
def source_and_result():
    root = Path(__file__).resolve().parents[1]
    source = verify_and_load_track_b_source(root / "artifacts/models/track_b/r6-track-b-v1", root)
    mapping = build_genomic_feature_mapping(source.feature_contract, source.model_feature_names)
    return source, extract_prognostic_feature_effects(source, mapping)


def _write(tmp_path, monkeypatch, source_and_result, name="output"):
    source, result = source_and_result
    monkeypatch.setattr(artifact_module, "_utc_now", lambda: "2026-09-19T12:00:00+00:00")
    monkeypatch.setattr(artifact_module, "_git_commit", lambda root: "r8-fixed-commit")
    return write_prognostic_feature_bundle(result, source, tmp_path / name)


def test_pre_audit_bundle_has_exact_five_file_set(tmp_path, monkeypatch, source_and_result) -> None:
    bundle = _write(tmp_path, monkeypatch, source_and_result)
    assert {path.name for path in bundle.iterdir()} == {
        "feature_effects.csv",
        "metadata.json",
        "summary.json",
        "report.md",
        "checksums.sha256",
    }


def test_feature_csv_has_exact_columns_and_sixty_eight_rows(
    tmp_path, monkeypatch, source_and_result
) -> None:
    bundle = _write(tmp_path, monkeypatch, source_and_result)
    with (bundle / "feature_effects.csv").open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
    assert tuple(reader.fieldnames or ()) == FEATURE_EFFECTS_CSV_COLUMNS
    assert len(rows) == 68


def test_bundle_refuses_overwrite(tmp_path, monkeypatch, source_and_result) -> None:
    source, result = source_and_result
    output = tmp_path / "output"
    _write(tmp_path, monkeypatch, source_and_result)
    with pytest.raises(FileExistsError, match="already exists"):
        write_prognostic_feature_bundle(result, source, output)


def test_bundle_contains_no_patient_identifier_duration_event_prediction_or_risk(
    tmp_path, monkeypatch, source_and_result
) -> None:
    bundle = _write(tmp_path, monkeypatch, source_and_result)
    payload = "\n".join(
        path.read_text(encoding="utf-8") for path in bundle.iterdir() if path.suffix != ".sha256"
    ).lower()
    for prohibited in (
        "patient_id",
        "patient identifier",
        "overall_survival_months",
        "event_observed",
        "prediction_digest",
        "risk_score",
    ):
        assert prohibited not in payload
    assert not any(path.suffix == ".pkl" for path in bundle.iterdir())


def test_float_json_csv_and_newline_serialization_are_deterministic(
    tmp_path, monkeypatch, source_and_result
) -> None:
    bundle = _write(tmp_path, monkeypatch, source_and_result)
    for name in ("metadata.json", "summary.json"):
        raw = (bundle / name).read_bytes()
        assert raw.endswith(b"\n") and b"\r\n" not in raw
        json.loads(raw)
    raw_csv = (bundle / "feature_effects.csv").read_bytes()
    assert raw_csv.endswith(b"\n") and b"\r\n" not in raw_csv
    first = next(csv.DictReader(raw_csv.decode("utf-8").splitlines()))
    assert first["beta"] == format(float(first["beta"]), ".17g")


def test_fixed_context_reproduces_bundle_bytes(tmp_path, monkeypatch, source_and_result) -> None:
    first = _write(tmp_path, monkeypatch, source_and_result, "first")
    second = _write(tmp_path, monkeypatch, source_and_result, "second")
    assert {path.name: path.read_bytes() for path in first.iterdir()} == {
        path.name: path.read_bytes() for path in second.iterdir()
    }


def test_metadata_contains_exact_r6_lineage_mapping_threshold_and_runtime(
    tmp_path, monkeypatch, source_and_result
) -> None:
    source, _ = source_and_result
    bundle = _write(tmp_path, monkeypatch, source_and_result)
    metadata = json.loads((bundle / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["analysis_id"] == "r8-prognostic-features-v1"
    assert metadata["source"]["experiment_id"] == "r6-track-b-v1"
    assert metadata["source"]["hashes"]["cox_model.pkl"] == source.verified_digests["cox_model.pkl"]
    assert metadata["feature_contract"]["encoded_r6_total"] == 80
    assert metadata["feature_contract"]["excluded_clinical"] == 12
    assert metadata["feature_contract"]["analyzed_total"] == 68
    assert len(metadata["feature_contract"]["genomic_mapping"]) == 68
    assert metadata["coefficient_contract"]["coef_eps"] == 1e-6
    assert metadata["runtime"]["generation_git_commit"] == "r8-fixed-commit"


def test_summary_counts_are_derived_from_effects_not_constants(
    tmp_path, monkeypatch, source_and_result
) -> None:
    source, result = source_and_result
    expected_active = sum(effect.is_active for effect in result.effects)
    bundle = _write(tmp_path, monkeypatch, source_and_result)
    summary = json.loads((bundle / "summary.json").read_text(encoding="utf-8"))
    assert summary["activity_counts"]["active"] == expected_active
    assert summary["activity_counts"]["effectively_zero"] == 68 - expected_active
    refresh_prognostic_feature_checksums(bundle)
