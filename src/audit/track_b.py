"""Independent persisted-bundle audit for the 25 frozen R6 requirements."""

from __future__ import annotations

import csv
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
import pandas as pd

from src.artifacts.track_b import refresh_track_b_checksums, verify_track_b_reload
from src.artifacts.survival import load_trusted_pickle
from src.contracts.analysis import SerializableContract
from src.data.metabric import MetabricPaths
from src.preprocessing.track_b import track_b_feature_names
from src.training.track_b import prepare_track_b_run


_R5_COMMIT = "93f669cf7638a09bcff0434f9f93590aa0c552e1"
_R5_BUNDLE = Path("artifacts/models/track_a/r5a-track-a-baseline-v1")
_R5_PATHS = (
    "src/training/track_a.py",
    "src/modeling/survival.py",
    "src/artifacts/survival.py",
    "src/preprocessing/pipelines.py",
    _R5_BUNDLE.as_posix(),
)


@dataclass(frozen=True, slots=True)
class TrackBAuditCheck(SerializableContract):
    number: int
    name: str
    passed: bool
    evidence: str


@dataclass(frozen=True, slots=True)
class TrackBAuditReport(SerializableContract):
    status: str
    checks: tuple[TrackBAuditCheck, ...]
    full_test_suite_summary: str


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _r5_artifacts_match(root: Path) -> bool:
    bundle = root / _R5_BUNDLE
    for line in (bundle / "checksums.sha256").read_text(encoding="utf-8").splitlines():
        expected, name = line.split(maxsplit=1)
        if _sha256(bundle / name) != expected:
            return False
    diff = subprocess.run(
        ["git", "diff", "--quiet", _R5_COMMIT, "--", *_R5_PATHS],
        cwd=root,
        check=False,
    )
    return diff.returncode == 0


def _check(number: int, name: str, passed: bool, evidence: str) -> TrackBAuditCheck:
    return TrackBAuditCheck(number, name, bool(passed), evidence)


def _report_contains_metrics(report: str, metrics: dict) -> bool:
    values = (
        metrics["track_a"]["validation"]["c_index"],
        metrics["track_a"]["test"]["c_index"],
        metrics["track_b"]["validation"]["c_index"],
        metrics["track_b"]["test"]["c_index"],
        metrics["comparison"]["validation_delta"],
        metrics["comparison"]["test_delta"],
    )
    return all(f"{float(value):.6f}" in report for value in values)


def audit_persisted_track_b(
    bundle: Path,
    *,
    repository_root: Path,
    full_test_suite_passed: bool,
    full_test_suite_summary: str,
) -> TrackBAuditReport:
    """Evaluate all 25 frozen R6 checks without fitting or rewriting source data."""
    root = Path(repository_root).resolve()
    artifact_root = Path(bundle).resolve()
    metadata = json.loads((artifact_root / "metadata.json").read_text(encoding="utf-8"))
    metrics = json.loads((artifact_root / "metrics.json").read_text(encoding="utf-8"))
    contract = json.loads((artifact_root / "feature_contract.json").read_text(encoding="utf-8"))
    report = (artifact_root / "report.md").read_text(encoding="utf-8")
    with (artifact_root / "validation_leaderboard.csv").open(newline="", encoding="utf-8") as stream:
        leaderboard = list(csv.DictReader(stream))
    prepared_run = prepare_track_b_run(MetabricPaths.from_repository_root(root))
    canonical = pd.read_csv(root / metadata["dataset"]["prepared_path"], low_memory=False)
    manifest = pd.read_csv(root / metadata["dataset"]["manifest_path"])
    preprocessor = load_trusted_pickle(artifact_root / "preprocessor.pkl", trusted=True)
    model = load_trusted_pickle(artifact_root / "cox_model.pkl", trusted=True)
    test_matrix = np.asarray(preprocessor.transform(prepared_run.test_predictors), dtype=float)
    model_names = track_b_feature_names(preprocessor)
    mutation_indices = [index for index, name in enumerate(model_names) if name.endswith("_mut_present")]
    columns = preprocessor.named_steps["columns"]
    expression_scaler = columns.named_transformers_["expression"]
    mutation_transformer = columns.named_transformers_["mutation"]
    clinical = columns.named_transformers_["clinical"]
    clinical_columns = clinical.named_steps["columns"]
    train_expression = prepared_run.train_predictors.loc[:, contract["expression_features"]].to_numpy(float)
    train_tumor_median = float(prepared_run.train_predictors["tumor_size"].median())
    train_er_mode = str(prepared_run.train_predictors["er_status_measured_by_ihc"].mode(dropna=True).iloc[0])
    fitted_tumor_median = float(
        clinical_columns.named_transformers_["tumor_size"].named_steps["imputer"].statistics_[0]
    )
    fitted_er_mode = str(
        clinical_columns.named_transformers_["er_status"].named_steps["imputer"].statistics_[0]
    )
    converged = [row for row in leaderboard if row["status"] == "CONVERGED"]
    winner = max(converged, key=lambda row: float(row["validation_c_index"]))
    selected = metadata["selected_configuration"]
    reload = verify_track_b_reload(artifact_root, prepared_run)
    source_hash_matches = _sha256(root / metadata["dataset"]["prepared_path"]) == metadata["dataset"]["prepared_sha256"]
    split_counts = manifest["split"].value_counts().to_dict()
    expected_clinical = list(prepared_run.schema.clinical_features)
    forbidden = set(contract["raw_feature_names"]) - set(
        contract["clinical_features"] + contract["expression_features"] + contract["mutation_features"]
    )
    delta_validation = (
        metrics["track_b"]["validation"]["c_index"]
        - metrics["track_a"]["validation"]["c_index"]
    )
    delta_test = metrics["track_b"]["test"]["c_index"] - metrics["track_a"]["test"]["c_index"]
    checks = (
        _check(1, "Active canonical dataset", len(canonical) == 1904 and len(canonical.columns) == 693 and source_hash_matches, f"rows={len(canonical)}, columns={len(canonical.columns)}, sha256_match={source_hash_matches}"),
        _check(2, "Locked split", split_counts == {"train": 1332, "validation": 286, "test": 286}, str(split_counts)),
        _check(3, "Frozen R5 unchanged", _r5_artifacts_match(root), "R5 source paths match commit and local bundle checksums"),
        _check(4, "Exactly seven frozen clinical predictors", contract["clinical_feature_count"] == 7 and contract["clinical_features"] == expected_clinical, str(contract["clinical_features"])),
        _check(5, "Exactly 50 selected expression predictors", contract["expression_feature_count"] == 50, "count=50"),
        _check(6, "Exactly 18 selected mutation predictors", contract["mutation_feature_count"] == 18, "count=18"),
        _check(7, "No unapproved raw predictor", contract["raw_feature_count"] == 75 and not forbidden and len(set(contract["raw_feature_names"])) == 75, f"raw_count={contract['raw_feature_count']}"),
        _check(8, "Existing R4D mutation semantics", mutation_transformer.__class__.__module__ == "src.preprocessing.track_b" and "existing R4D classifier" in metadata["mutation_policy"], f"transformer={mutation_transformer.__class__.__module__}.{mutation_transformer.__class__.__name__}; {metadata['mutation_policy']}"),
        _check(9, "Source mutation annotations unchanged", source_hash_matches, f"prepared_sha256={metadata['dataset']['prepared_sha256']}"),
        _check(10, "Final mutation matrix binary", len(mutation_indices) == 18 and set(np.unique(test_matrix[:, mutation_indices])).issubset({0.0, 1.0}), f"mutation_columns={len(mutation_indices)}"),
        _check(11, "Expression scaler fit on train only", int(expression_scaler.n_samples_seen_) == len(prepared_run.train_predictors) and np.allclose(expression_scaler.mean_, train_expression.mean(axis=0)), f"n_samples_seen={expression_scaler.n_samples_seen_}"),
        _check(12, "Clinical preprocessing fit on train only", np.isclose(fitted_tumor_median, train_tumor_median) and fitted_er_mode == train_er_mode, f"tumor_median={fitted_tumor_median}, er_mode={fitted_er_mode}"),
        _check(13, "Validation and test are transform-only", metadata["expression_preprocessing"].endswith("validation/test transform only") and int(expression_scaler.n_samples_seen_) == 1332, metadata["expression_preprocessing"]),
        _check(14, "Survival event coding not inverted", metadata["survival_contract"]["event_observed_value"] == 1 and metadata["survival_contract"]["event_inverted"] is False and set(canonical[metadata["survival_contract"]["event_column"]].unique()) == {0, 1}, str(metadata["survival_contract"])),
        _check(15, "Track A/B comparison cohorts identical", metrics["track_a"]["validation"]["cohort_fingerprint"] == metrics["track_b"]["validation"]["cohort_fingerprint"] and metrics["track_a"]["test"]["cohort_fingerprint"] == metrics["track_b"]["test"]["cohort_fingerprint"], "validation and test fingerprints match"),
        _check(16, "Hyperparameters selected from validation only", float(winner["penalizer"]) == float(selected["penalizer"]) and float(winner["l1_ratio"]) == float(selected["l1_ratio"]) and metadata["selection_policy"] == "maximum validation C-index only", f"winner={selected}"),
        _check(17, "Test excluded from candidate selection", metadata["candidate_test_evaluation_count"] == 0, "candidate_test_evaluation_count=0"),
        _check(18, "Only frozen winner evaluated on test", metadata["winner_test_evaluation_count"] == 1, "winner_test_evaluation_count=1"),
        _check(19, "New model uses current Cognivex train data", metadata["runtime"]["prepared_sha256"] == prepared_run.prepared_sha256 and metadata["cohorts"]["train"]["row_count"] == 1332, "current prepared hash and train count match"),
        _check(20, "Historical engineer pickles unused", model.__class__.__module__ == "src.modeling.track_b" and "cognivex_ml" not in json.dumps(metadata).lower(), f"persisted_model={model.__class__.__module__}.{model.__class__.__name__}; no engineer artifact path in metadata"),
        _check(21, "Persisted artifact reload", reload.passed, f"risk_sha256={reload.risk_sha256}"),
        _check(22, "Saved feature order matches training", reload.feature_order_matches and list(model_names) == contract["model_feature_names"], f"feature_count={len(model_names)}"),
        _check(23, "Metrics file matches report", _report_contains_metrics(report, metrics), "all A/B metrics and deltas rendered"),
        _check(24, "A versus B deltas correct", np.isclose(delta_validation, metrics["comparison"]["validation_delta"]) and np.isclose(delta_test, metrics["comparison"]["test_delta"]), f"validation={delta_validation}, test={delta_test}"),
        _check(25, "Full tests remain green", full_test_suite_passed, full_test_suite_summary),
    )
    return TrackBAuditReport(
        status="PASS" if all(check.passed for check in checks) else "BLOCKED",
        checks=checks,
        full_test_suite_summary=full_test_suite_summary,
    )


def write_track_b_audit(bundle: Path, audit: TrackBAuditReport) -> Path:
    """Persist aggregate audit evidence and refresh the bundle checksums."""
    path = Path(bundle) / "audit.json"
    path.write_text(json.dumps(audit.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    refresh_track_b_checksums(Path(bundle))
    return path
