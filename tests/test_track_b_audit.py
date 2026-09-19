"""Persisted R6 25-check audit tests."""

from __future__ import annotations

import json
from pathlib import Path

from r6_helpers import make_single_candidate_track_b_run
from src.artifacts.track_b import write_track_b_artifacts
from src.audit.track_b import audit_persisted_track_b, write_track_b_audit


def test_persisted_track_b_passes_all_25_required_audit_checks(tmp_path: Path) -> None:
    prepared, selection, result = make_single_candidate_track_b_run()
    bundle = write_track_b_artifacts(selection, result, prepared, tmp_path)

    audit = audit_persisted_track_b(
        bundle,
        repository_root=prepared.repository_root,
        full_test_suite_passed=True,
        full_test_suite_summary="controlled full-suite evidence",
    )

    assert audit.status == "PASS"
    assert len(audit.checks) == 25
    assert [check.number for check in audit.checks] == list(range(1, 26))
    assert all(check.passed for check in audit.checks)

    write_track_b_audit(bundle, audit)
    payload = json.loads((bundle / "audit.json").read_text(encoding="utf-8"))
    checksums = (bundle / "checksums.sha256").read_text(encoding="utf-8")

    assert payload["status"] == "PASS"
    assert len(payload["checks"]) == 25
    assert "audit.json" in checksums


def test_audit_fails_check_25_without_full_suite_evidence(tmp_path: Path) -> None:
    prepared, selection, result = make_single_candidate_track_b_run()
    bundle = write_track_b_artifacts(selection, result, prepared, tmp_path)

    audit = audit_persisted_track_b(
        bundle,
        repository_root=prepared.repository_root,
        full_test_suite_passed=False,
        full_test_suite_summary="not run",
    )

    assert audit.status == "BLOCKED"
    assert audit.checks[-1].number == 25
    assert audit.checks[-1].passed is False
