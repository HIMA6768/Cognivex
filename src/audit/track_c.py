"""Independent persisted-bundle audit for the 28 frozen R7 requirements."""

from __future__ import annotations

import csv
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

import numpy as np
import pandas as pd

from src.artifacts.survival import load_trusted_pickle
from src.artifacts.track_c import (
    refresh_track_c_checksums,
    verify_track_c_bundle,
    verify_track_c_checksums,
)
from src.contracts.analysis import SerializableContract
from src.data import TRACK_C_CLASS_ORDER
from src.data.metabric import MetabricPaths
from src.modeling.track_c import TRACK_C_CANDIDATES
from src.training.track_c import prepare_track_c_run


R5_COMMIT = "93f669cf7638a09bcff0434f9f93590aa0c552e1"
R6_COMMIT = "49a8414c1aa828c07cfa9f9dd207a2bdf311b078"
R5_BUNDLE = Path("artifacts/models/track_a/r5a-track-a-baseline-v1")
R6_BUNDLE = Path("artifacts/models/track_b/r6-track-b-v1")
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
    "scripts/train_track_b.py",
)

AUDIT_CHECK_NAMES = (
    "Active canonical dataset unchanged",
    "Locked split unchanged",
    "R5 unchanged",
    "R6 unchanged",
    "Exactly 68 genomic predictors",
    "Exactly 50 expression predictors",
    "Exactly 18 mutation predictors",
    "No clinical predictors",
    "Correct subtype target",
    "NC excluded only from Track C",
    "Six intended classes present",
    "Existing R4D mutation semantics reused",
    "Source mutation annotations unchanged",
    "Final mutation inputs binary",
    "Train-only scaling and preprocessing",
    "Validation and test are transform-only",
    "Exactly four approved model families",
    "Winner selected by validation Macro-F1",
    "Test cannot influence selection",
    "Only frozen winner evaluated on test",
    "Historical engineer pickles unused",
    "Final artifact reload succeeds",
    "Predictions reproduce after reload",
    "Class order persisted",
    "Feature order persisted",
    "Confusion matrix sums correctly",
    "Report and metrics agree",
    "Full test suite green",
)


@dataclass(frozen=True, slots=True)
class TrackCAuditCheck(SerializableContract):
    number: int
    name: str
    passed: bool
    evidence: str


@dataclass(frozen=True, slots=True)
class TrackCAuditReport(SerializableContract):
    status: str
    checks: tuple[TrackCAuditCheck, ...]
    full_test_suite_summary: str


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _bundle_checksums_match(bundle: Path) -> bool:
    root = Path(bundle)
    checksum = root / "checksums.sha256"
    if not checksum.is_file():
        return False
    for line in checksum.read_text(encoding="utf-8").splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) != 2 or not (root / parts[1]).is_file() or _sha256(root / parts[1]) != parts[0]:
            return False
    return True


def _frozen_state_matches(root: Path, commit: str, paths: tuple[str, ...], bundle: Path) -> bool:
    source = subprocess.run(
        ["git", "diff", "--quiet", commit, "--", *paths],
        cwd=root,
        check=False,
    ).returncode == 0
    return source and _bundle_checksums_match(root / bundle)


def _check(number: int, passed: bool, evidence: str) -> TrackCAuditCheck:
    return TrackCAuditCheck(number, AUDIT_CHECK_NAMES[number - 1], bool(passed), evidence)


def finalize_track_c_audit(
    checks: tuple[TrackCAuditCheck, ...],
    full_test_suite_summary: str,
) -> TrackCAuditReport:
    if tuple(check.number for check in checks) != tuple(range(1, 29)):
        raise ValueError("Track C audit must contain checks 1 through 28")
    if tuple(check.name for check in checks) != AUDIT_CHECK_NAMES:
        raise ValueError("Track C audit check names must match the frozen contract")
    return TrackCAuditReport(
        status="PASS" if all(check.passed for check in checks) else "BLOCKED",
        checks=checks,
        full_test_suite_summary=full_test_suite_summary,
    )


def read_pytest_summary(path: Path) -> tuple[bool, str]:
    """Read the literal final pytest passed-summary line from an evidence file."""
    lines = [line.strip() for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    summaries = [line for line in lines if re.search(r"\b\d+ passed\b", line)]
    if not summaries:
        raise ValueError("full-suite evidence contains no passed-summary line")
    summary = summaries[-1]
    passed = not re.search(r"\b(?:failed|error|errors)\b", summary, flags=re.IGNORECASE)
    return passed, summary


def _report_matches(report: str, metrics: dict) -> bool:
    return all(
        f"{float(metrics['test'][name]):.6f}" in report
        for name in ("macro_f1", "weighted_f1", "accuracy", "balanced_accuracy")
    )


def audit_persisted_track_c(
    bundle: Path,
    *,
    repository_root: Path,
    full_test_suite_passed: bool,
    full_test_suite_summary: str,
) -> TrackCAuditReport:
    """Evaluate the 28 R7 checks without fitting or modifying artifacts/data."""
    root = Path(repository_root).resolve()
    artifact_root = Path(bundle).resolve()
    metadata = json.loads((artifact_root / "metadata.json").read_text(encoding="utf-8"))
    metrics = json.loads((artifact_root / "metrics.json").read_text(encoding="utf-8"))
    contract = json.loads((artifact_root / "feature_contract.json").read_text(encoding="utf-8"))
    report = (artifact_root / "report.md").read_text(encoding="utf-8")
    with (artifact_root / "validation_leaderboard.csv").open(newline="", encoding="utf-8") as stream:
        leaderboard = list(csv.DictReader(stream))
    prepared_path = root / "data/metabric/prepared/METABRIC_prepared.csv"
    manifest_path = root / "data/metabric/metadata/manifest.csv"
    canonical = pd.read_csv(prepared_path, low_memory=False)
    manifest = pd.read_csv(manifest_path)
    run = prepare_track_c_run(MetabricPaths.from_repository_root(root))
    pipeline = load_trusted_pickle(artifact_root / "pipeline.pkl", trusted=True)
    selected_key = metadata["selection"]["selected_model"]
    selected_definition = next(
        (item for item in metadata["candidate_definitions"] if item["key"] == selected_key),
        None,
    )
    preprocessor = pipeline.named_steps.get("preprocessor") if hasattr(pipeline, "named_steps") else None
    columns = preprocessor.named_steps.get("columns") if preprocessor is not None else None
    mutation_transformer = columns.named_transformers_.get("mutation") if columns is not None else None
    expression_transformer = columns.named_transformers_.get("expression") if columns is not None else None
    try:
        test_order = list(run.test.split.patient_ids)
        transformed = preprocessor.transform(run.test.split.predictors.loc[test_order])
        transformed = np.asarray(transformed, dtype=float)
        mutation_binary = set(np.unique(transformed[:, 50:])).issubset({0.0, 1.0})
        bundle_verification = verify_track_c_bundle(artifact_root, run.test)
    except Exception:
        mutation_binary = False
        bundle_verification = None
    winner = leaderboard[0]
    for row in leaderboard[1:]:
        score = float(row["macro_f1"])
        best = float(winner["macro_f1"])
        if score > best and not math.isclose(score, best, abs_tol=1e-12, rel_tol=0):
            winner = row
    source_hash_matches = _sha256(prepared_path) == metadata["dataset"]["prepared_sha256"]
    manifest_hash_matches = _sha256(manifest_path) == metadata["dataset"]["manifest_sha256"]
    split_counts = manifest["split"].value_counts().to_dict()
    frozen_keys = [item.key for item in TRACK_C_CANDIDATES]
    candidate_keys = [item["key"] for item in metadata["candidate_definitions"]]
    classifier = pipeline.named_steps.get("classifier") if hasattr(pipeline, "named_steps") else pipeline
    scaler_ok = True
    if selected_definition and selected_definition["scale_expression"]:
        scaler_ok = (
            expression_transformer is not None
            and hasattr(expression_transformer, "n_samples_seen_")
            and int(expression_transformer.n_samples_seen_) == run.selection.train.row_count
        )
    transform_only = scaler_ok and run.selection.train.row_count == 1330
    reload_ok = bundle_verification.reload if bundle_verification is not None else None
    checks = (
        _check(1, len(canonical) == 1904 and len(canonical.columns) == 693 and source_hash_matches, f"rows={len(canonical)}, columns={len(canonical.columns)}, sha256_match={source_hash_matches}"),
        _check(2, split_counts == {"train": 1332, "validation": 286, "test": 286} and manifest_hash_matches, f"counts={split_counts}, sha256_match={manifest_hash_matches}"),
        _check(3, _frozen_state_matches(root, R5_COMMIT, R5_PATHS, R5_BUNDLE), "R5 dedicated source paths and local artifact checksums"),
        _check(4, _frozen_state_matches(root, R6_COMMIT, R6_PATHS, R6_BUNDLE), "R6 dedicated source paths and local artifact checksums"),
        _check(5, contract["raw_feature_count"] == 68 and len(contract["raw_feature_names"]) == 68, f"count={contract['raw_feature_count']}"),
        _check(6, contract["expression_feature_count"] == 50, f"count={contract['expression_feature_count']}"),
        _check(7, contract["mutation_feature_count"] == 18, f"count={contract['mutation_feature_count']}"),
        _check(8, contract["clinical_feature_count"] == 0 and not contract["clinical_features"], "clinical_count=0"),
        _check(9, metadata["target"] == "pam50_+_claudin-low_subtype", metadata["target"]),
        _check(10, metadata["excluded_labels"] == ["NC", "missing", "unsupported"] and len(canonical) == 1904, "Track C eligibility only; canonical cohort retained"),
        _check(11, metadata["class_order"] == list(TRACK_C_CLASS_ORDER), str(metadata["class_order"])),
        _check(12, mutation_transformer is not None and mutation_transformer.__class__.__module__ == "src.preprocessing.track_b", f"transformer={getattr(mutation_transformer.__class__, '__module__', 'missing') if mutation_transformer is not None else 'missing'}"),
        _check(13, source_hash_matches, metadata["dataset"]["prepared_sha256"]),
        _check(14, mutation_binary, "all transformed selected mutation values are in {0,1}"),
        _check(15, scaler_ok, f"selected_model={selected_key}, train_rows={run.selection.train.row_count}"),
        _check(16, transform_only, "fitted preprocessing sample count remains train eligible count; holdouts transform only"),
        _check(17, candidate_keys == frozen_keys and len(leaderboard) == 4, str(candidate_keys)),
        _check(18, winner["key"] == selected_key and metadata["selection"]["primary_metric"] == "validation_macro_f1", f"winner={winner['key']}"),
        _check(19, metadata["selection"]["candidate_test_evaluation_count"] == 0, "candidate_test_evaluation_count=0"),
        _check(20, metadata["selection"]["winner_test_evaluation_count"] == 1, "winner_test_evaluation_count=1"),
        _check(21, "cognivex_ml" not in classifier.__class__.__module__, classifier.__class__.__module__),
        _check(22, reload_ok is not None and reload_ok.passed, "trusted local pipeline reload"),
        _check(23, reload_ok is not None and reload_ok.prediction_digest_matches, metrics["test_prediction_digest"]),
        _check(24, reload_ok is not None and reload_ok.class_order_matches, str(contract["class_order"])),
        _check(25, reload_ok is not None and reload_ok.feature_order_matches, f"feature_count={contract['model_feature_count']}"),
        _check(26, sum(sum(row) for row in metrics["test"]["confusion_matrix"]) == metrics["test"]["row_count"] == run.test.split.row_count, f"sum={sum(sum(row) for row in metrics['test']['confusion_matrix'])}"),
        _check(27, _report_matches(report, metrics) and reload_ok is not None and reload_ok.metrics_match, "rendered test metrics and persisted metrics agree"),
        _check(28, full_test_suite_passed, full_test_suite_summary),
    )
    return finalize_track_c_audit(checks, full_test_suite_summary)


def write_track_c_audit(bundle: Path, audit: TrackCAuditReport) -> Path:
    """Persist aggregate audit evidence, then update bundle checksums."""
    path = Path(bundle) / "audit.json"
    path.write_text(json.dumps(audit.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    refresh_track_c_checksums(Path(bundle))
    return path
