from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import pytest

from src.data import TRACK_C_CLASS_ORDER


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "artifacts/models/track_c/r7-track-c-v1"


def _json(name: str):
    return json.loads((BUNDLE / name).read_text(encoding="utf-8"))


def test_canonical_r7_nonbinary_bundle_has_expected_identity_and_all_28_audit_checks() -> None:
    if not (BUNDLE / "audit.json").is_file():
        pytest.skip("final audit is persisted only after the first complete-suite evidence run")
    metadata = _json("metadata.json")
    contract = _json("feature_contract.json")
    audit = _json("audit.json")
    with (BUNDLE / "validation_leaderboard.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))

    winner = rows[0]
    for row in rows[1:]:
        score = float(row["macro_f1"])
        best = float(winner["macro_f1"])
        if score > best and not math.isclose(score, best, abs_tol=1e-12, rel_tol=0):
            winner = row
    assert metadata["experiment_id"] == "r7-track-c-v1"
    assert metadata["track"] == "C"
    assert metadata["selection"]["selected_model"] == winner["key"]
    assert contract["expression_feature_count"] == 50
    assert contract["mutation_feature_count"] == 18
    assert contract["raw_feature_count"] == 68
    assert contract["clinical_feature_count"] == 0
    assert tuple(contract["class_order"]) == TRACK_C_CLASS_ORDER
    assert metadata["feature_contract"]["raw_feature_order"] == contract["raw_feature_names"]
    assert metadata["feature_contract"]["model_feature_order"] == contract["model_feature_names"]
    assert metadata["metrics"]["validation"]["macro_f1"] > 0
    assert metadata["metrics"]["test"]["macro_f1"] > 0
    assert metadata["runtime"]["python_version"]
    assert metadata["runtime"]["sklearn_version"]
    assert metadata["runtime"]["git_commit"]
    assert audit["status"] == "PASS"
    assert [item["number"] for item in audit["checks"]] == list(range(1, 29))
    assert all(item["passed"] for item in audit["checks"])


def test_canonical_r7_metrics_report_confusion_and_classification_report_agree() -> None:
    metrics = _json("metrics.json")
    classification = _json("classification_report.json")
    report = (BUNDLE / "report.md").read_text(encoding="utf-8")
    with (BUNDLE / "confusion_matrix.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.reader(stream))
    matrix = [[int(value) for value in row[1:]] for row in rows[1:]]

    assert len(matrix) == 6 and all(len(row) == 6 for row in matrix)
    assert sum(sum(row) for row in matrix) == metrics["test"]["row_count"]
    assert matrix == metrics["test"]["confusion_matrix"]
    assert classification == metrics["test"]["classification_report"]
    for name in ("macro_f1", "weighted_f1", "accuracy", "balanced_accuracy"):
        assert f"{metrics['test'][name]:.6f}" in report
    assert "The test set was not used for model selection." in report


def test_canonical_r7_evidence_contains_no_patient_rows_and_preserves_r5_r6_data_hashes() -> None:
    metadata = _json("metadata.json")
    r6_metadata = json.loads(
        (ROOT / "artifacts/models/track_b/r6-track-b-v1/metadata.json").read_text(encoding="utf-8")
    )
    prepared_hash = hashlib.sha256(
        (ROOT / "data/metabric/prepared/METABRIC_prepared.csv").read_bytes()
    ).hexdigest()
    manifest_hash = hashlib.sha256(
        (ROOT / "data/metabric/metadata/manifest.csv").read_bytes()
    ).hexdigest()

    assert metadata["dataset"]["prepared_sha256"] == prepared_hash == r6_metadata["dataset"]["prepared_sha256"]
    assert metadata["dataset"]["manifest_sha256"] == manifest_hash == r6_metadata["dataset"]["manifest_sha256"]
    for path in BUNDLE.iterdir():
        if path.name != "pipeline.pkl" and path.is_file():
            content = path.read_text(encoding="utf-8").lower()
            assert "patient_id" not in content
            assert "prediction_rows" not in content
