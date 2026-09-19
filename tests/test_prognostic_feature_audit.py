from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import subprocess
import sys

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
from src.audit import prognostic_features as audit_module
from src.audit.prognostic_features import (
    R8_AUDIT_CHECK_NAMES,
    PrognosticFeatureAuditCheck,
    audit_prognostic_feature_bundle,
    finalize_prognostic_feature_audit,
    write_prognostic_feature_audit,
)


ROOT = Path(__file__).resolve().parents[1]
AUDIT_SCRIPT = ROOT / "scripts/audit_prognostic_features.py"
GOOD_SUMMARY = "300 passed in 123.45s"


@pytest.fixture()
def bundle(tmp_path, monkeypatch):
    r6 = ROOT / "artifacts/models/track_b/r6-track-b-v1"
    source = verify_and_load_track_b_source(r6, ROOT)
    mapping = build_genomic_feature_mapping(source.feature_contract, source.model_feature_names)
    result = extract_prognostic_feature_effects(source, mapping)
    monkeypatch.setattr(artifact_module, "_utc_now", lambda: "2026-09-19T12:00:00+00:00")
    return r6, write_prognostic_feature_bundle(result, source, tmp_path)


def _checks(passed: bool = True) -> tuple[PrognosticFeatureAuditCheck, ...]:
    return tuple(
        PrognosticFeatureAuditCheck(number, name, passed, "evidence")
        for number, name in enumerate(R8_AUDIT_CHECK_NAMES, start=1)
    )


def test_audit_names_are_exactly_numbered_one_through_thirty() -> None:
    assert len(R8_AUDIT_CHECK_NAMES) == 30
    assert R8_AUDIT_CHECK_NAMES[0] == "Canonical R6 bundle identity is correct."
    assert R8_AUDIT_CHECK_NAMES[-1] == "R9 was not started."
    report = finalize_prognostic_feature_audit(_checks(), GOOD_SUMMARY)
    assert tuple(check.number for check in report.checks) == tuple(range(1, 31))


def test_audit_check_numbers_are_unique() -> None:
    checks = list(_checks())
    checks[-1] = replace(checks[-1], number=29)
    with pytest.raises(ValueError, match="1 through 30"):
        finalize_prognostic_feature_audit(tuple(checks), GOOD_SUMMARY)


def test_any_failed_check_makes_status_blocked() -> None:
    checks = list(_checks())
    checks[10] = replace(checks[10], passed=False)
    assert finalize_prognostic_feature_audit(tuple(checks), GOOD_SUMMARY).status == "BLOCKED"


def test_only_thirty_true_checks_make_status_pass() -> None:
    assert finalize_prognostic_feature_audit(_checks(), GOOD_SUMMARY).status == "PASS"


def test_check_twenty_nine_requires_literal_successful_full_suite_summary(bundle) -> None:
    r6, output = bundle
    report = audit_prognostic_feature_bundle(output, r6, ROOT, "collection complete")
    assert report.checks[28].passed is False
    assert report.status == "BLOCKED"


def test_audit_checks_frozen_r5_r6_r7_sources_and_artifacts(bundle) -> None:
    r6, output = bundle
    report = audit_prognostic_feature_bundle(output, r6, ROOT, GOOD_SUMMARY)
    assert report.checks[3].passed
    assert report.checks[4].passed
    assert report.checks[0].passed


def test_audit_detects_fitting_imports_or_calls(monkeypatch) -> None:
    monkeypatch.setattr(audit_module, "R8_RUNTIME_PATHS", audit_module.R8_RUNTIME_PATHS + ("src/training/track_b.py",))
    assert audit_module._r8_has_no_fitting(ROOT) is False


def test_audit_writer_adds_audit_before_final_checksum_manifest(bundle) -> None:
    r6, output = bundle
    report = write_prognostic_feature_audit(output, r6, ROOT, GOOD_SUMMARY)
    assert report.status == "PASS"
    assert (output / "audit.json").is_file()
    assert "audit.json" in (output / "checksums.sha256").read_text(encoding="utf-8")


def test_final_checksum_manifest_covers_audit_and_excludes_itself(bundle) -> None:
    r6, output = bundle
    write_prognostic_feature_audit(output, r6, ROOT, GOOD_SUMMARY)
    names = [line.split("  ", 1)[1] for line in (output / "checksums.sha256").read_text().splitlines()]
    assert set(names) == {"audit.json", "feature_effects.csv", "metadata.json", "report.md", "summary.json"}
    assert "checksums.sha256" not in names


def test_audit_rerun_replaces_bootstrap_summary_with_final_summary(bundle) -> None:
    r6, output = bundle
    write_prognostic_feature_audit(output, r6, ROOT, "299 passed, 1 skipped in 120.00s")
    final = write_prognostic_feature_audit(output, r6, ROOT, GOOD_SUMMARY)
    persisted = json.loads((output / "audit.json").read_text(encoding="utf-8"))
    assert final.full_test_suite_summary == GOOD_SUMMARY
    assert persisted["full_test_suite_summary"] == GOOD_SUMMARY


def test_audit_rerun_does_not_regenerate_feature_effects(bundle) -> None:
    r6, output = bundle
    path = output / "feature_effects.csv"
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    write_prognostic_feature_audit(output, r6, ROOT, "299 passed, 1 skipped in 120.00s")
    write_prognostic_feature_audit(output, r6, ROOT, GOOD_SUMMARY)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_audit_cli_help_and_blocked_exit_code(bundle, tmp_path) -> None:
    help_result = subprocess.run(
        [sys.executable, str(AUDIT_SCRIPT), "--help"], cwd=ROOT, capture_output=True, text=True
    )
    assert help_result.returncode == 0
    r6, output = bundle
    evidence = tmp_path / "pytest.txt"
    evidence.write_text("1 failed, 299 passed in 120.00s\n", encoding="utf-8")
    blocked = subprocess.run(
        [
            sys.executable,
            str(AUDIT_SCRIPT),
            "--bundle",
            str(output),
            "--source-bundle",
            str(r6),
            "--full-test-suite-summary-file",
            str(evidence),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert blocked.returncode == 1
    assert "BLOCKED" in blocked.stdout
