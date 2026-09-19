from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from r7_helpers import ROOT, make_synthetic_track_c_run
from src.artifacts.track_c import write_track_c_artifacts
from src.audit.track_c import (
    AUDIT_CHECK_NAMES,
    TrackCAuditCheck,
    finalize_track_c_audit,
    read_pytest_summary,
    audit_persisted_track_c,
)


def test_r7_audit_contains_exactly_numbered_28_checks_for_persisted_bundle(tmp_path: Path) -> None:
    prepared, selection, result = make_synthetic_track_c_run()
    bundle = write_track_c_artifacts(selection, result, prepared, tmp_path)

    audit = audit_persisted_track_c(
        bundle,
        repository_root=ROOT,
        full_test_suite_passed=True,
        full_test_suite_summary="250 passed in 1.00s",
    )

    assert tuple(check.number for check in audit.checks) == tuple(range(1, 29))
    assert tuple(check.name for check in audit.checks) == AUDIT_CHECK_NAMES
    assert audit.status == "BLOCKED"  # synthetic fixture is intentionally not canonical


def test_any_failed_audit_check_makes_status_blocked() -> None:
    checks = tuple(
        TrackCAuditCheck(index, name, index != 7, "evidence")
        for index, name in enumerate(AUDIT_CHECK_NAMES, start=1)
    )

    report = finalize_track_c_audit(checks, "250 passed in 1.00s")

    assert report.status == "BLOCKED"


def test_all_28_true_checks_make_status_pass() -> None:
    checks = tuple(
        TrackCAuditCheck(index, name, True, "evidence")
        for index, name in enumerate(AUDIT_CHECK_NAMES, start=1)
    )
    assert finalize_track_c_audit(checks, "250 passed in 1.00s").status == "PASS"


def test_check_28_fails_without_full_suite_evidence(tmp_path: Path) -> None:
    prepared, selection, result = make_synthetic_track_c_run()
    bundle = write_track_c_artifacts(selection, result, prepared, tmp_path)

    audit = audit_persisted_track_c(
        bundle,
        repository_root=ROOT,
        full_test_suite_passed=False,
        full_test_suite_summary="not supplied",
    )

    assert audit.checks[27].number == 28
    assert audit.checks[27].passed is False


def test_audit_verifies_r5_and_r6_source_and_bundle_checksums(tmp_path: Path) -> None:
    prepared, selection, result = make_synthetic_track_c_run()
    bundle = write_track_c_artifacts(selection, result, prepared, tmp_path)

    audit = audit_persisted_track_c(
        bundle,
        repository_root=ROOT,
        full_test_suite_passed=True,
        full_test_suite_summary="250 passed in 1.00s",
    )

    assert audit.checks[2].name == "R5 unchanged"
    assert audit.checks[2].passed is True
    assert audit.checks[3].name == "R6 unchanged"
    assert audit.checks[3].passed is True


def test_audit_cli_help_runs_from_repository_root() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/audit_track_c.py", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "--full-test-suite-summary-file" in completed.stdout
    assert "--full-test-suite-passed" in completed.stdout


def test_audit_cli_reads_literal_pytest_summary_from_evidence_file(tmp_path: Path) -> None:
    evidence = tmp_path / "pytest.txt"
    evidence.write_text("progress\n250 passed, 2 warnings in 10.00s\n", encoding="utf-8")

    passed, summary = read_pytest_summary(evidence)

    assert passed is True
    assert summary == "250 passed, 2 warnings in 10.00s"
    invalid = tmp_path / "invalid.txt"
    invalid.write_text("suite did not finish\n", encoding="utf-8")
    with pytest.raises(ValueError, match="passed-summary"):
        read_pytest_summary(invalid)
