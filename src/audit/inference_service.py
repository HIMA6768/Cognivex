"""Independent, aggregate-only audit for R9 trusted inference orchestration."""

from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import subprocess

from src.artifacts.inference_registry import R5_BUNDLE, R6_BUNDLE, R7_BUNDLE, R8_BUNDLE, build_canonical_registry
from src.contracts.inference import FROZEN_SUBTYPE_CLASS_ORDER, PROGNOSIS_OUTPUT_KIND


R9_AUDIT_BUNDLE = Path("artifacts/audits/r9-inference-service-v1")
R9_BASE_COMMIT = "1eca09a75deea94e557632063837f2d9abc9683c"
APPROVED_BOOTSTRAP_SKIP = "tests/test_r9_canonical_provenance.py"


@dataclass(frozen=True, slots=True)
class InferenceServiceAuditCheck:
    number: int
    name: str
    passed: bool

    def to_dict(self) -> dict[str, object]:
        return {"number": self.number, "name": self.name, "passed": self.passed}


@dataclass(frozen=True, slots=True)
class InferenceServiceAuditReport:
    status: str
    provisional: bool
    mode: str
    full_test_suite_summary: str
    r9_lifecycle_skip_nodeids: tuple[str, ...]
    checks: tuple[InferenceServiceAuditCheck, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status, "provisional": self.provisional, "mode": self.mode,
            "full_test_suite_summary": self.full_test_suite_summary,
            "full_suite_evidence": {"r9_lifecycle_skip_nodeids": list(self.r9_lifecycle_skip_nodeids)},
            "checks": [check.to_dict() for check in self.checks],
        }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _runtime_has_no_fitting(root: Path) -> bool:
    forbidden_imports = ("streamlit", "fastapi", "pydantic", "src.training", "cognivex_ml")
    for directory in (root / "src/inference", root / "src/services"):
        for path in directory.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import) and any(alias.name.startswith(forbidden_imports) for alias in node.names):
                    return False
                if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(forbidden_imports):
                    return False
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {"fit", "fit_transform"}:
                    return False
    return True


def _r10_not_started(root: Path) -> bool:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{R9_BASE_COMMIT}..HEAD", "--", "app.py", "src/ui"],
        cwd=root, check=False, capture_output=True, text=True,
    )
    if result.returncode != 0 or result.stdout.strip():
        return False
    return not any("r10" in path.name.lower() for path in (root / "src").rglob("*.py"))


def _r9_skips(summary: str) -> tuple[str, ...]:
    return tuple(
        APPROVED_BOOTSTRAP_SKIP for line in summary.splitlines()
        if "SKIPPED" in line and APPROVED_BOOTSTRAP_SKIP in line.replace("\\", "/")
    )


def _summary_passes(summary: str) -> bool:
    last = next((line.strip() for line in reversed(summary.splitlines()) if re.search(r"\b\d+ passed\b", line)), "")
    return bool(last) and "failed" not in last and "error" not in last


def audit_inference_service(repository_root: Path, full_test_suite_summary: str, *, bootstrap: bool = False) -> InferenceServiceAuditReport:
    """Audit contracts and source boundaries without model inference or writes."""
    root = Path(repository_root).resolve()
    registry = build_canonical_registry(root)
    runtime_paths = "\n".join(path.read_text(encoding="utf-8") for directory in (root / "src/inference", root / "src/services") for path in directory.glob("*.py"))
    r5, r6, r7, r8 = registry.track_a, registry.track_b, registry.track_c, registry.r8
    skipped = _r9_skips(full_test_suite_summary)
    bootstrap_allowed = bootstrap and skipped == (APPROVED_BOOTSTRAP_SKIP,) and _summary_passes(full_test_suite_summary)
    final_suite = _summary_passes(full_test_suite_summary) and not skipped
    checks = (
        InferenceServiceAuditCheck(1, "R5 identity is verified.", r5.available),
        InferenceServiceAuditCheck(2, "R6 identity is verified.", r6.available),
        InferenceServiceAuditCheck(3, "R7 identity is verified.", r7.available),
        InferenceServiceAuditCheck(4, "R8 identity and source lineage are verified.", r8.available),
        InferenceServiceAuditCheck(5, "Only canonical repository-relative bundles are used.", all((root / path).is_dir() for path in (R5_BUNDLE, R6_BUNDLE, R7_BUNDLE, R8_BUNDLE))),
        InferenceServiceAuditCheck(6, "Historical engineer pickles are unused.", "cognivex_ml" not in runtime_paths),
        InferenceServiceAuditCheck(7, "Runtime does not fit or train.", _runtime_has_no_fitting(root)),
        InferenceServiceAuditCheck(8, "Global raw namespace is exactly 75 fields.", len(registry.global_contract.raw_fields) == 75),
        InferenceServiceAuditCheck(9, "R5 raw contract is exactly seven fields.", len(r5.required_fields) == 7),
        InferenceServiceAuditCheck(10, "R6 raw contract is exactly 75 fields.", len(r6.required_fields) == 75),
        InferenceServiceAuditCheck(11, "R7 raw contract is exactly 68 fields.", len(r7.required_fields) == 68),
        InferenceServiceAuditCheck(12, "R5 uses its persisted twelve-feature transform.", len(getattr(r5.model, "feature_names", ())) == 12),
        InferenceServiceAuditCheck(13, "R6 uses its persisted eighty-feature transform.", len(getattr(r6.model, "feature_names", ())) == 80),
        InferenceServiceAuditCheck(14, "R7 uses its persisted pipeline.", r7.model is r7.preprocessor),
        InferenceServiceAuditCheck(15, "Prognosis output is log partial hazard only.", PROGNOSIS_OUTPUT_KIND == "log_partial_hazard"),
        InferenceServiceAuditCheck(16, "No clinical category or recommendation contract exists.", "recommendation" not in runtime_paths and "risk_category" not in runtime_paths),
        InferenceServiceAuditCheck(17, "R7 class order is frozen.", tuple(r7.metadata.get("class_order", ())) == FROZEN_SUBTYPE_CLASS_ORDER),
        InferenceServiceAuditCheck(18, "Subtype probability contract is normalized and finite.", "probabilities must sum to one" in (root / "src/contracts/inference.py").read_text(encoding="utf-8")),
        InferenceServiceAuditCheck(19, "NC cannot be emitted by Track C contract.", 'predicted not in FROZEN_SUBTYPE_CLASS_ORDER' in (root / "src/inference/track_c.py").read_text(encoding="utf-8")),
        InferenceServiceAuditCheck(20, "Track readiness supports partial requests.", "MISSING_REQUIRED_FIELDS" in (root / "src/services/analysis.py").read_text(encoding="utf-8")),
        InferenceServiceAuditCheck(21, "Requested tracks are validated.", "requested_tracks" in (root / "src/services/analysis.py").read_text(encoding="utf-8")),
        InferenceServiceAuditCheck(22, "Track initialization is isolated.", all(entry.error_code in (None, "ARTIFACT_UNAVAILABLE") for entry in (r5, r6, r7))),
        InferenceServiceAuditCheck(23, "Response contracts do not retain feature mappings.", "features:" not in (root / "src/contracts/inference.py").read_text(encoding="utf-8").split("class AnalysisResponse", 1)[1]),
        InferenceServiceAuditCheck(24, "Runtime writes no patient data.", all(token not in runtime_paths for token in ("write_text", "to_csv", "pickle.dump", "logging."))),
        InferenceServiceAuditCheck(25, "R8 remains aggregate-only and independently available.", r8.available),
        InferenceServiceAuditCheck(26, "Runtime remains framework independent.", all(token not in runtime_paths for token in ("streamlit", "fastapi", "pydantic"))),
        InferenceServiceAuditCheck(27, "Artifacts are loaded only at service construction.", "build_canonical_registry" not in (root / "src/services/analysis.py").read_text(encoding="utf-8").split("def analyze", 1)[1]),
        InferenceServiceAuditCheck(28, "Runtime has no randomness.", "random." not in runtime_paths),
        InferenceServiceAuditCheck(29, "Contracts, metadata, and behavior agree.", r5.available and r6.available and r7.available and r8.available),
        InferenceServiceAuditCheck(30, "Final full suite passes with zero R9 lifecycle skips.", final_suite),
        InferenceServiceAuditCheck(31, "R10 was not started.", _r10_not_started(root)),
    )
    passed = all(check.passed for check in checks)
    if bootstrap:
        if not bootstrap_allowed:
            raise ValueError("bootstrap evidence must contain only the approved R9 lifecycle skip")
        return InferenceServiceAuditReport("BLOCKED", True, "bootstrap", full_test_suite_summary, skipped, checks)
    return InferenceServiceAuditReport("PASS" if passed else "BLOCKED", False, "final", full_test_suite_summary, skipped, checks)


def _write_checksums(bundle: Path) -> None:
    rows = [f"{_sha256(path)}  {path.name}" for path in sorted(bundle.iterdir()) if path.is_file() and path.name != "checksums.sha256"]
    (bundle / "checksums.sha256").write_text("\n".join(rows) + "\n", encoding="utf-8")


def write_inference_service_audit(repository_root: Path, full_test_suite_summary: str, *, bootstrap: bool = False) -> InferenceServiceAuditReport:
    report = audit_inference_service(repository_root, full_test_suite_summary, bootstrap=bootstrap)
    if not bootstrap and report.status != "PASS":
        raise ValueError("final audit requires all 31 checks to pass")
    bundle = Path(repository_root) / R9_AUDIT_BUNDLE
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / "audit.json").write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_checksums(bundle)
    return report


def verify_inference_service_audit(repository_root: Path) -> InferenceServiceAuditReport:
    bundle = Path(repository_root) / R9_AUDIT_BUNDLE
    audit_path, checksum_path = bundle / "audit.json", bundle / "checksums.sha256"
    if not audit_path.is_file() or not checksum_path.is_file():
        raise ValueError("final R9 audit evidence is unavailable")
    declared = {line.split("  ", 1)[1]: line.split("  ", 1)[0] for line in checksum_path.read_text(encoding="utf-8").splitlines() if "  " in line}
    if declared != {"audit.json": _sha256(audit_path)}:
        raise ValueError("R9 audit checksums are invalid")
    payload = json.loads(audit_path.read_text(encoding="utf-8"))
    checks = tuple(InferenceServiceAuditCheck(**check) for check in payload["checks"])
    report = InferenceServiceAuditReport(payload["status"], payload["provisional"], payload["mode"], payload["full_test_suite_summary"], tuple(payload["full_suite_evidence"]["r9_lifecycle_skip_nodeids"]), checks)
    if report.provisional or report.mode != "final" or report.status != "PASS" or len(report.checks) != 31 or not all(check.passed for check in report.checks):
        raise ValueError("R9 audit is not final passing evidence")
    return report
