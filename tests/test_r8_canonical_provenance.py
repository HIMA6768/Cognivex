from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "artifacts/analysis/r8-prognostic-features-v1"
R6 = ROOT / "artifacts/models/track_b/r6-track-b-v1"


def _json(name: str) -> dict:
    return json.loads((BUNDLE / name).read_text(encoding="utf-8"))


def _rows() -> list[dict[str, str]]:
    with (BUNDLE / "feature_effects.csv").open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def test_canonical_r8_bundle_matches_approved_pre_and_post_audit_file_sets() -> None:
    names = {path.name for path in BUNDLE.iterdir()}
    pre_audit = {
        "feature_effects.csv",
        "metadata.json",
        "summary.json",
        "report.md",
        "checksums.sha256",
    }
    assert names in (pre_audit, pre_audit | {"audit.json"})


def test_canonical_r8_evidence_has_68_rows_50_expression_18_mutation_and_zero_clinical() -> None:
    rows = _rows()
    metadata = _json("metadata.json")
    assert len(rows) == 68
    assert sum(row["feature_type"] == "expression" for row in rows) == 50
    assert sum(row["feature_type"] == "mutation_presence" for row in rows) == 18
    assert metadata["feature_contract"]["clinical"] == 0


def test_canonical_activity_counts_are_current_evidence_24_and_44() -> None:
    rows = _rows()
    summary = _json("summary.json")
    assert sum(row["is_active"] == "true" for row in rows) == 24
    assert sum(row["is_active"] == "false" for row in rows) == 44
    assert summary["activity_counts"] == {"active": 24, "effectively_zero": 44}


def test_canonical_metadata_matches_frozen_r6_hashes_and_configuration() -> None:
    metadata = _json("metadata.json")
    hashes = metadata["source"]["hashes"]
    assert hashes["cox_model.pkl"] == "5d312d905974772ad0967ba8dbd47bce7de81dc3cca5fdee54f8ad259a3d86f2"
    assert hashes["preprocessor.pkl"] == "d23c26e85ef30b1d85c87055b2e824ecb0624af7c3ddedceacd75c5bfbe6acb5"
    assert hashes["feature_contract.json"] == "97888b7cbb655d542a4a3cafc42bdfe1d65e267d95cc8e84f125d2a4003fff27"
    assert metadata["source"]["prepared_sha256"] == "e18275dac2b8b11d158093785816ae04d3b2466217d5af47a6290e5927146c29"
    assert metadata["source"]["manifest_sha256"] == "d4c884a92a988d935ca19664e1da3bb1bbcc02037dad96a31991779c4589cb9e"
    assert metadata["model"] == {
        "adapter_class": "PenalizedCoxPHAdapter",
        "fitter_class": "CoxPHFitter",
        "baseline_estimation_method": "breslow",
        "penalizer": 0.05,
        "l1_ratio": 0.5,
        "alpha": 0.05,
    }


def test_canonical_report_summary_and_feature_table_agree() -> None:
    rows = _rows()
    summary = _json("summary.json")
    report = (BUNDLE / "report.md").read_text(encoding="utf-8")
    assert summary["total"] == len(rows) == 68
    assert sum(line.startswith("| ") and line.split("|")[1].strip().isdigit() for line in report.splitlines()) == 68
    assert all(f"| {row['rank']} | {row['raw_feature_name']} |" in report for row in rows)


def test_canonical_audit_has_thirty_passing_checks() -> None:
    if not (BUNDLE / "audit.json").exists():
        pytest.skip("audit is generated after full-suite evidence")
    audit = _json("audit.json")
    assert audit["status"] == "PASS"
    assert len(audit["checks"]) == 30
    assert [check["number"] for check in audit["checks"]] == list(range(1, 31))
    assert all(check["passed"] for check in audit["checks"])


def test_canonical_audit_records_final_no_lifecycle_skip_pytest_summary() -> None:
    if not (BUNDLE / "audit.json").exists():
        pytest.skip("audit is generated after full-suite evidence")
    summary = _json("audit.json")["full_test_suite_summary"]
    assert "passed" in summary
    assert "failed" not in summary.lower()
    assert "audit is generated after full-suite evidence" not in summary


def test_canonical_checksums_verify_without_ignored_pickles() -> None:
    lines = (BUNDLE / "checksums.sha256").read_text(encoding="utf-8").splitlines()
    entries = dict(line.split("  ", 1)[::-1] for line in lines)
    expected = {path.name for path in BUNDLE.iterdir() if path.is_file() and path.name != "checksums.sha256"}
    assert set(entries) == expected
    assert not any(name.endswith(".pkl") for name in entries)
    assert all(hashlib.sha256((BUNDLE / name).read_bytes()).hexdigest() == digest for name, digest in entries.items())
