"""Independent 30-check audit for frozen-model R8 prognostic feature analysis."""

from __future__ import annotations

import ast
import csv
from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
import subprocess

from src.analysis.prognostic_features import (
    R6_CLINICAL_MODEL_FEATURES,
    build_genomic_feature_mapping,
    validate_genomic_mapping_authorities,
)
from src.artifacts.prognostic_features import (
    R6_BUNDLE_RELATIVE,
    refresh_prognostic_feature_checksums,
    verify_and_load_track_b_source,
    verify_prognostic_feature_bundle,
)
from src.contracts import COEF_EPS, DIRECTION_DISPLAY_TEXT, EffectDirection
from src.contracts.analysis import SerializableContract


R8_AUDIT_CHECK_NAMES = (
    "Canonical R6 bundle identity is correct.",
    "R6 model checksum and identity are unchanged.",
    "R6 preprocessor and feature contract are unchanged.",
    "R5 source and artifacts are unchanged.",
    "R7 source and artifacts are unchanged.",
    "R8 performs no model or preprocessing fitting.",
    "Exactly 68 genomic predictors are analyzed.",
    "Exactly 50 expression predictors are analyzed.",
    "Exactly 18 mutation-presence predictors are analyzed.",
    "Zero clinical predictors enter the genomic ranking.",
    "Raw-to-model genomic mapping matches all frozen R6 orders.",
    "Every genomic coefficient exists exactly once.",
    "Every beta is finite.",
    "Every abs_beta equals abs(beta).",
    "Every hazard ratio equals exp(beta) within the frozen tolerance.",
    "Every hazard ratio is finite and positive.",
    "COEF_EPS and is_active are applied exactly.",
    "Direction labels and display text match beta and tolerance.",
    "Ranking is descending by absolute beta.",
    "Exact ties follow frozen genomic order.",
    "Effectively-zero features remain present and are labeled consistently.",
    "Model-reported inferential values are not used for ranking, activity, or filtering.",
    "Historical engineer pickles were not loaded.",
    "No patient-level data is persisted.",
    "Report, summary, and feature table agree.",
    "Metadata lineage points to the exact frozen R6 source.",
    "Final bundle checksums verify.",
    "Artifact generation is reproducible and read-only relative to R6.",
    "The complete test suite passes.",
    "R9 had not started at the frozen R8 final evidence commit.",
)

R5_COMMIT = "93f669cf7638a09bcff0434f9f93590aa0c552e1"
R6_COMMIT = "49a8414c1aa828c07cfa9f9dd207a2bdf311b078"
R7_COMMIT = "97e6434634c3391acbd6e5e50dca316bef4ad6fb"
R8_FINAL_EVIDENCE_COMMIT = "0662bda058f0c93f758f29e0fb033aca24e06721"
R5_BUNDLE = Path("artifacts/models/track_a/r5a-track-a-baseline-v1")
R7_BUNDLE = Path("artifacts/models/track_c/r7-track-c-v1")
_CANONICAL_DEPLOYMENT_PICKLES = (
    (R5_BUNDLE / "preprocessor.pkl").as_posix(),
    (R5_BUNDLE / "cox_model.pkl").as_posix(),
    (Path("artifacts/models/track_b/r6-track-b-v1") / "preprocessor.pkl").as_posix(),
    (Path("artifacts/models/track_b/r6-track-b-v1") / "cox_model.pkl").as_posix(),
    (R7_BUNDLE / "pipeline.pkl").as_posix(),
)
R5_PATHS = (
    "src/training/track_a.py",
    "src/modeling/survival.py",
    "src/artifacts/survival.py",
    "src/preprocessing/pipelines.py",
)
R6_PATHS = (
    "src/training/track_b.py",
    "src/modeling/track_b.py",
    "src/artifacts/track_b.py",
    "src/preprocessing/track_b.py",
    "src/audit/track_b.py",
    "scripts/train_track_b.py",
    "scripts/audit_track_b.py",
)
R7_PATHS = (
    "src/training/track_c.py",
    "src/modeling/track_c.py",
    "src/artifacts/track_c.py",
    "src/preprocessing/track_c.py",
    "scripts/train_track_c.py",
)
R8_RUNTIME_PATHS = (
    "src/contracts/prognostic_features.py",
    "src/analysis/prognostic_features.py",
    "src/artifacts/prognostic_features.py",
    "src/audit/prognostic_features.py",
    "scripts/analyze_prognostic_features.py",
    "scripts/verify_prognostic_feature_artifacts.py",
    "scripts/audit_prognostic_features.py",
)


@dataclass(frozen=True, slots=True)
class PrognosticFeatureAuditCheck(SerializableContract):
    number: int
    name: str
    passed: bool
    evidence: str


@dataclass(frozen=True, slots=True)
class PrognosticFeatureAuditReport(SerializableContract):
    status: str
    checks: tuple[PrognosticFeatureAuditCheck, ...]
    full_test_suite_summary: str


def _check(number: int, passed: bool, evidence: str) -> PrognosticFeatureAuditCheck:
    return PrognosticFeatureAuditCheck(number, R8_AUDIT_CHECK_NAMES[number - 1], bool(passed), evidence)


def finalize_prognostic_feature_audit(
    checks: tuple[PrognosticFeatureAuditCheck, ...],
    full_test_suite_summary: str,
) -> PrognosticFeatureAuditReport:
    if tuple(check.number for check in checks) != tuple(range(1, 31)):
        raise ValueError("R8 audit must contain checks 1 through 30")
    if tuple(check.name for check in checks) != R8_AUDIT_CHECK_NAMES:
        raise ValueError("R8 audit check names must match the frozen contract")
    if len({check.number for check in checks}) != 30:
        raise ValueError("R8 audit check numbers must be unique")
    return PrognosticFeatureAuditReport(
        status="PASS" if all(check.passed for check in checks) else "BLOCKED",
        checks=checks,
        full_test_suite_summary=full_test_suite_summary,
    )


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _bundle_checksums_match(bundle: Path) -> bool:
    root = Path(bundle)
    try:
        entries = [line.split("  ", 1) for line in (root / "checksums.sha256").read_text().splitlines()]
    except OSError:
        return False
    expected = {path.name for path in root.iterdir() if path.is_file() and path.name != "checksums.sha256"}
    return (
        all(len(parts) == 2 for parts in entries)
        and {parts[1] for parts in entries} == expected
        and all(_sha256(root / name) == digest for digest, name in entries)
    )


def _frozen_state_matches(root: Path, commit: str, paths: tuple[str, ...], bundle: Path) -> bool:
    bundle_prefix = f"{bundle.as_posix()}/"
    deployment_pickle_exclusions = tuple(
        f":(exclude){path}"
        for path in _CANONICAL_DEPLOYMENT_PICKLES
        if path.startswith(bundle_prefix)
    )
    unchanged = subprocess.run(
        [
            "git",
            "diff",
            "--quiet",
            commit,
            "--",
            *paths,
            bundle.as_posix(),
            *deployment_pickle_exclusions,
        ],
        cwd=root,
        check=False,
    ).returncode == 0
    return unchanged and _bundle_checksums_match(root / bundle)


def _r9_was_not_started_at_r8_milestone(root: Path) -> bool:
    """Evaluate the historical R8 milestone tree, never the later working tree."""
    result = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", R8_FINAL_EVIDENCE_COMMIT, "--", "src/inference", "scripts/run_inference.py"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and not result.stdout.strip()


def _r8_has_no_fitting(root: Path) -> bool:
    forbidden_import_prefixes = ("src.training", "cognivex_ml")
    for relative in R8_RUNTIME_PATHS:
        path = Path(root) / relative
        if not path.is_file():
            return False
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            return False
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                if any(alias.name.startswith(forbidden_import_prefixes) for alias in node.names):
                    return False
            elif isinstance(node, ast.ImportFrom):
                if (node.module or "").startswith(forbidden_import_prefixes):
                    return False
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in {"fit", "fit_transform"}:
                    return False
    return True


def _successful_pytest_summary(summary: str) -> bool:
    return bool(re.search(r"\b\d+ passed\b", summary)) and not bool(
        re.search(r"\b(?:failed|error|errors)\b", summary, flags=re.IGNORECASE)
    )


def audit_prognostic_feature_bundle(
    bundle: Path,
    r6_bundle: Path,
    repository_root: Path,
    full_test_suite_summary: str,
) -> PrognosticFeatureAuditReport:
    """Evaluate exactly 30 aggregate, no-fit R8 checks."""
    root = Path(repository_root).resolve()
    artifact_root = Path(bundle).resolve()
    source = verify_and_load_track_b_source(r6_bundle, root)
    mapping = build_genomic_feature_mapping(source.feature_contract, source.model_feature_names)
    try:
        validate_genomic_mapping_authorities(mapping, source)
        mapping_ok = True
    except ValueError:
        mapping_ok = False
    verification = verify_prognostic_feature_bundle(artifact_root, r6_bundle, root)
    with (artifact_root / "feature_effects.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    metadata = json.loads((artifact_root / "metadata.json").read_text(encoding="utf-8"))
    summary = json.loads((artifact_root / "summary.json").read_text(encoding="utf-8"))
    report = (artifact_root / "report.md").read_text(encoding="utf-8")
    betas = [float(row["beta"]) for row in rows]
    abs_betas = [float(row["abs_beta"]) for row in rows]
    hazards = [float(row["hazard_ratio"]) for row in rows]
    feature_types = [row["feature_type"] for row in rows]
    unique_names = {row["model_feature_name"] for row in rows}
    expected_order = sorted(
        rows,
        key=lambda row: (-float(row["abs_beta"]), int(row["frozen_genomic_order"])),
    )
    ranking_ok = [row["model_feature_name"] for row in rows] == [
        row["model_feature_name"] for row in expected_order
    ] and [int(row["rank"]) for row in rows] == list(range(1, 69))
    ties_ok = all(
        not math.isclose(abs_betas[index - 1], abs_betas[index], rel_tol=0, abs_tol=0)
        or int(rows[index - 1]["frozen_genomic_order"]) < int(rows[index]["frozen_genomic_order"])
        for index in range(1, len(rows))
    )
    activity_ok = all(
        (row["is_active"] == "true") == (abs(float(row["beta"])) > COEF_EPS)
        for row in rows
    ) and metadata["coefficient_contract"]["coef_eps"] == COEF_EPS
    direction_ok = True
    for row in rows:
        beta = float(row["beta"])
        direction = (
            EffectDirection.HIGHER
            if beta > COEF_EPS
            else EffectDirection.LOWER
            if beta < -COEF_EPS
            else EffectDirection.EFFECTIVELY_ZERO
        )
        direction_ok &= row["direction"] == direction.value
        direction_ok &= row["direction_display"] == DIRECTION_DISPLAY_TEXT[direction]
    zero_rows = [row for row in rows if abs(float(row["beta"])) <= COEF_EPS]
    forbidden_payload = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in artifact_root.iterdir()
        if path.is_file() and path.suffix != ".sha256"
    ).lower()
    no_patient_data = not any(
        marker in forbidden_payload
        for marker in ("patient_id", "overall_survival_months", "event_observed", "risk_score", "prediction_digest")
    ) and not any(path.suffix == ".pkl" for path in artifact_root.iterdir())
    lineage = metadata.get("source", {})
    lineage_ok = (
        lineage.get("experiment_id") == "r6-track-b-v1"
        and lineage.get("bundle_path") == R6_BUNDLE_RELATIVE.as_posix()
        and lineage.get("hashes", {}).get("cox_model.pkl") == source.verified_digests["cox_model.pkl"]
        and lineage.get("hashes", {}).get("preprocessor.pkl") == source.verified_digests["preprocessor.pkl"]
        and lineage.get("hashes", {}).get("feature_contract.json") == source.verified_digests["feature_contract.json"]
    )
    inferred_policy = metadata.get("coefficient_contract", {}).get("inferential_fields", "")
    r9_absent = _r9_was_not_started_at_r8_milestone(root)
    checks = (
        _check(1, source.bundle == (root / R6_BUNDLE_RELATIVE).resolve(), str(source.bundle)),
        _check(2, source.verified_digests["cox_model.pkl"] == "5d312d905974772ad0967ba8dbd47bce7de81dc3cca5fdee54f8ad259a3d86f2", source.verified_digests["cox_model.pkl"]),
        _check(3, source.verified_digests["preprocessor.pkl"] == "d23c26e85ef30b1d85c87055b2e824ecb0624af7c3ddedceacd75c5bfbe6acb5" and source.verified_digests["feature_contract.json"] == "97888b7cbb655d542a4a3cafc42bdfe1d65e267d95cc8e84f125d2a4003fff27", "frozen preprocessor and contract hashes"),
        _check(4, _frozen_state_matches(root, R5_COMMIT, R5_PATHS, R5_BUNDLE), "R5 dedicated source paths and bundle checksums"),
        _check(5, _frozen_state_matches(root, R7_COMMIT, R7_PATHS, R7_BUNDLE), "R7 dedicated source paths and bundle checksums"),
        _check(6, _r8_has_no_fitting(root), "AST contains no training imports or fit/fit_transform calls"),
        _check(7, len(rows) == 68, f"rows={len(rows)}"),
        _check(8, feature_types.count("expression") == 50, f"expression={feature_types.count('expression')}"),
        _check(9, feature_types.count("mutation_presence") == 18, f"mutation_presence={feature_types.count('mutation_presence')}"),
        _check(10, not set(R6_CLINICAL_MODEL_FEATURES) & unique_names and metadata["feature_contract"]["clinical"] == 0, "clinical=0"),
        _check(11, mapping_ok, "persisted/preprocessor/adapter/params/summary orders agree"),
        _check(12, len(unique_names) == len(rows) == 68, f"unique={len(unique_names)}"),
        _check(13, all(math.isfinite(value) for value in betas), "all beta values finite"),
        _check(14, all(math.isclose(abs_beta, abs(beta), rel_tol=0, abs_tol=1e-15) for beta, abs_beta in zip(betas, abs_betas)), "abs_beta equals abs(beta)"),
        _check(15, all(math.isclose(hazard, math.exp(beta), rel_tol=1e-12, abs_tol=1e-12) for beta, hazard in zip(betas, hazards)), "hazard ratios equal exp(beta)"),
        _check(16, all(math.isfinite(value) and value > 0 for value in hazards), "all hazard ratios finite and positive"),
        _check(17, activity_ok, f"coef_eps={COEF_EPS}"),
        _check(18, direction_ok, "direction codes and display text recomputed"),
        _check(19, ranking_ok, "ranked by descending abs_beta then frozen order"),
        _check(20, ties_ok, "exact ties follow frozen genomic order"),
        _check(21, len(rows) == 68 and all(row["is_active"] == "false" and row["direction"] == EffectDirection.EFFECTIVELY_ZERO.value for row in zero_rows), f"effectively_zero={len(zero_rows)}"),
        _check(22, "never used for selection" in inferred_policy and ranking_ok, inferred_policy),
        _check(23, source.model.__class__.__module__ == "src.modeling.track_b" and "cognivex_ml" not in forbidden_payload, source.model.__class__.__module__),
        _check(24, no_patient_data, "aggregate-only files and no pickle artifacts"),
        _check(25, verification.checks.get("effects_match", False) and verification.checks.get("summary_match", False) and verification.checks.get("report_match", False) and summary["total"] == 68 and "| 68 |" in report, "table, summary, and report agree"),
        _check(26, lineage_ok, "metadata references exact frozen R6 hashes"),
        _check(27, verification.checks.get("checksums", False), "bundle checksum manifest verifies"),
        _check(28, verification.checks.get("source_unchanged", False) and verification.checks.get("bundle_unchanged", False), "read-only verifier preserved source and bundle bytes"),
        _check(29, _successful_pytest_summary(full_test_suite_summary), full_test_suite_summary),
        _check(30, r9_absent, "R9 absent at frozen R8 final evidence commit"),
    )
    return finalize_prognostic_feature_audit(checks, full_test_suite_summary)


def write_prognostic_feature_audit(
    bundle: Path,
    r6_bundle: Path,
    repository_root: Path,
    full_test_suite_summary: str,
) -> PrognosticFeatureAuditReport:
    """Write provisional/final audit passes and finish with verified checksums."""
    root = Path(bundle)
    provisional = audit_prognostic_feature_bundle(
        root, r6_bundle, repository_root, full_test_suite_summary
    )
    audit_path = root / "audit.json"
    audit_path.write_text(
        json.dumps(provisional.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    refresh_prognostic_feature_checksums(root)
    final = audit_prognostic_feature_bundle(root, r6_bundle, repository_root, full_test_suite_summary)
    audit_path.write_text(
        json.dumps(final.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    refresh_prognostic_feature_checksums(root)
    if not _bundle_checksums_match(root):
        raise RuntimeError("final R8 audit checksum manifest failed verification")
    return final
