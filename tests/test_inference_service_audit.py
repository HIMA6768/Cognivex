from __future__ import annotations

from pathlib import Path

from src.audit.inference_service import audit_inference_service


ROOT = Path(__file__).resolve().parents[1]


def test_audit_has_exactly_thirty_one_checks() -> None:
    report = audit_inference_service(ROOT, "250 passed in 10.00s")
    assert [check.number for check in report.checks] == list(range(1, 32))
    assert report.status == "PASS"
    assert report.provisional is False


def test_bootstrap_audit_is_explicitly_provisional_and_blocked() -> None:
    report = audit_inference_service(
        ROOT,
        "249 passed, 1 skipped in 10.00s\nSKIPPED [1] tests/test_r9_canonical_provenance.py: R9 audit is generated after bootstrap full-suite evidence",
        bootstrap=True,
    )
    assert report.provisional is True
    assert report.status == "BLOCKED"
    assert report.checks[29].passed is False


def test_bootstrap_accepts_pytest_windows_path_separator() -> None:
    report = audit_inference_service(
        ROOT,
        "249 passed, 1 skipped in 10.00s\nSKIPPED [1] tests\\test_r9_canonical_provenance.py: bootstrap",
        bootstrap=True,
    )
    assert report.r9_lifecycle_skip_nodeids == ("tests/test_r9_canonical_provenance.py",)


def test_check_thirty_one_scopes_r10_absence_to_frozen_r9_milestone() -> None:
    from src.audit import inference_service as audit

    assert (ROOT / "src/ui/analysis_service.py").is_file()
    assert audit._r10_was_not_started_at_r9_milestone(ROOT) is True
