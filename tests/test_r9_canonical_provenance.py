from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.audit.inference_service import R9_AUDIT_BUNDLE, verify_inference_service_audit


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / R9_AUDIT_BUNDLE / "audit.json"


def test_canonical_r9_audit_has_final_no_lifecycle_skip_summary() -> None:
    if not AUDIT.exists():
        pytest.skip("R9 audit is generated after bootstrap full-suite evidence")
    payload = json.loads(AUDIT.read_text(encoding="utf-8"))
    if payload["provisional"]:
        assert payload["mode"] == "bootstrap"
        assert payload["status"] == "BLOCKED"
        assert payload["full_suite_evidence"]["r9_lifecycle_skip_nodeids"] == ["tests/test_r9_canonical_provenance.py"]
    else:
        assert payload["mode"] == "final"
        assert payload["status"] == "PASS"
        assert payload["full_suite_evidence"]["r9_lifecycle_skip_nodeids"] == []
        assert verify_inference_service_audit(ROOT).status == "PASS"
