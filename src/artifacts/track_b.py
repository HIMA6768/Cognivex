"""Versioned local persistence and trusted reload verification for R6 Track B."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import pickle
from typing import Any, TYPE_CHECKING

import numpy as np

from src.contracts import TrackBExperimentResult
from src.preprocessing.track_b import track_b_feature_names

from .survival import load_trusted_pickle

if TYPE_CHECKING:
    from src.training.track_b import PreparedTrackBRun, SelectedTrackBModel


_INITIAL_BUNDLE_FILES = (
    "metadata.json",
    "metrics.json",
    "feature_contract.json",
    "validation_leaderboard.csv",
    "report.md",
    "preprocessor.pkl",
    "cox_model.pkl",
)


@dataclass(frozen=True, slots=True)
class TrackBReloadVerification:
    """Aggregate evidence that trusted persisted objects reproduce frozen output."""

    passed: bool
    feature_order_matches: bool
    max_absolute_risk_difference: float
    risk_sha256: str


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _risk_sha256(values: np.ndarray) -> str:
    canonical = np.asarray(values, dtype="<f8").reshape(-1)
    return hashlib.sha256(canonical.tobytes()).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _metric_payload(result: TrackBExperimentResult) -> dict[str, Any]:
    return {
        "track_a": {
            "validation": result.track_a_validation_metric.to_dict(),
            "test": result.track_a_test_metric.to_dict(),
        },
        "track_b": {
            "train": result.train_metric.to_dict(),
            "validation": result.validation_metric.to_dict(),
            "test": result.test_metric.to_dict(),
        },
        "comparison": {
            "validation_delta": result.validation_delta,
            "test_delta": result.test_delta,
        },
    }


def _contract_payload(result: TrackBExperimentResult) -> dict[str, Any]:
    contract = result.feature_contract
    return {
        "clinical_feature_count": len(contract.clinical_features),
        "clinical_features": list(contract.clinical_features),
        "expression_feature_count": len(contract.expression_features),
        "expression_features": list(contract.expression_features),
        "mutation_feature_count": len(contract.mutation_features),
        "mutation_features": list(contract.mutation_features),
        "raw_feature_count": len(contract.raw_features),
        "raw_feature_names": list(contract.raw_features),
        "model_feature_count": len(result.model_feature_names),
        "model_feature_names": list(result.model_feature_names),
    }


def _leaderboard_rows(result: TrackBExperimentResult) -> list[dict[str, Any]]:
    return [
        {
            "candidate_order": index,
            "penalizer": row.configuration.penalizer,
            "l1_ratio": row.configuration.l1_ratio,
            "status": row.status,
            "validation_c_index": row.validation_c_index,
            "error_message": row.error_message or "",
        }
        for index, row in enumerate(result.leaderboard, start=1)
    ]


def _report(result: TrackBExperimentResult) -> str:
    contract = result.feature_contract
    rows = _leaderboard_rows(result)
    leaderboard = "\n".join(
        f"| {row['candidate_order']} | {row['penalizer']:.2f} | {row['l1_ratio']:.1f} | "
        f"{row['status']} | "
        f"{'' if row['validation_c_index'] is None else f'{row['validation_c_index']:.6f}'} |"
        for row in rows
    )
    selected = result.selected_configuration
    return f"""# R6 Track B — Clinical + Genomic Survival Model

## Objective

Evaluate whether the explicit 68-feature genomic contract improves survival discrimination over the frozen seven-feature R5 clinical baseline. Track B was selected using validation performance only.

## Dataset and split

- Canonical prepared cohort: 1,904 patients
- Survival-eligible train: {result.train_cohort.row_count} ({result.train_cohort.event_count} events)
- Survival-eligible validation: {result.validation_cohort.row_count} ({result.validation_cohort.event_count} events)
- Survival-eligible test: {result.test_cohort.row_count} ({result.test_cohort.event_count} events)
- Duration: `overall_survival_months`
- Event: `overall_survival` (`1` = deceased/event; `0` = living/censored)

## Feature contract and preprocessing

- Frozen R5 clinical predictors: {len(contract.clinical_features)}
- Explicit selected expression predictors: {len(contract.expression_features)}; standardized by a train-fitted `StandardScaler`
- Explicit selected mutation predictors: {len(contract.mutation_features)}; existing R4D annotation semantics map absence `0` to 0 and valid non-zero annotations to 1
- Raw predictors: {len(contract.raw_features)}
- Encoded model features: {len(result.model_feature_names)}
- Clinical imputation and reference-category encoding reuse the frozen R5 train-fitted contract
- Validation and test use transform-only preprocessing

## Validation leaderboard

| Order | Penalizer | L1 ratio | Status | Validation C-index |
|---:|---:|---:|---|---:|
{leaderboard}

Selected configuration: penalizer `{selected.penalizer}`, l1 ratio `{selected.l1_ratio}`.

## Track A versus Track B

| Split | Track A C-index | Track B C-index | Delta B - A |
|---|---:|---:|---:|
| Validation | {result.track_a_validation_metric.c_index:.6f} | {result.validation_metric.c_index:.6f} | {result.validation_delta:.6f} |
| Test | {result.track_a_test_metric.c_index:.6f} | {result.test_metric.c_index:.6f} | {result.test_delta:.6f} |

Track B was selected using validation performance only. Candidate models were not evaluated on test; only the frozen validation winner received one final test evaluation.

## Limitations

- This research/educational result is not a clinical decision system.
- The selected genomic panel and regularization grid are predefined engineering inputs, not causal or biological evidence.
- Coefficients must not be interpreted as Track D biological conclusions.
- External validation and calibration remain out of scope.
"""


def refresh_track_b_checksums(bundle: Path) -> None:
    """Rewrite deterministic checksums for all bundle files except the checksum file."""
    root = Path(bundle)
    names = sorted(path.name for path in root.iterdir() if path.name != "checksums.sha256")
    (root / "checksums.sha256").write_text(
        "".join(f"{_sha256(root / name)}  {name}\n" for name in names),
        encoding="utf-8",
    )


def write_track_b_artifacts(
    selection: SelectedTrackBModel,
    result: TrackBExperimentResult,
    prepared: PreparedTrackBRun,
    output_root: Path,
) -> Path:
    """Write one non-overwriting aggregate R6 bundle plus trusted local pickles."""
    if selection.contract != result.feature_contract or selection.contract != prepared.contract:
        raise ValueError("Track B feature contracts do not agree")
    bundle = Path(output_root) / result.experiment_id
    if bundle.exists():
        raise FileExistsError(f"experiment bundle already exists: {bundle}")
    bundle.mkdir(parents=True)

    test_matrix = np.asarray(selection.preprocessor.transform(prepared.test_predictors), dtype=float)
    test_risk = selection.model.predict_risk(test_matrix)
    metadata = {
        "schema_version": result.schema_version,
        "experiment_id": result.experiment_id,
        "track": "B",
        "task": "clinical_genomic_survival",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "prepared_path": "data/metabric/prepared/METABRIC_prepared.csv",
            "prepared_sha256": prepared.prepared_sha256,
            "manifest_path": "data/metabric/metadata/manifest.csv",
            "manifest_sha256": prepared.manifest_sha256,
            "patient_count": 1904,
            "column_count": 693,
        },
        "cohorts": {
            "train": result.train_cohort.to_dict(),
            "validation": result.validation_cohort.to_dict(),
            "test": result.test_cohort.to_dict(),
        },
        "survival_contract": {
            "duration_column": prepared.schema.survival_time_column,
            "event_column": prepared.schema.survival_event_column,
            "event_observed_value": 1,
            "censored_value": 0,
            "event_inverted": False,
        },
        "mutation_policy": (
            "existing R4D classifier: trimmed/numeric zero is absent; valid non-zero "
            "annotation is present; missing/malformed values fail"
        ),
        "clinical_preprocessing": "frozen R5 train-fitted preprocessing",
        "expression_preprocessing": "train-fitted StandardScaler; validation/test transform only",
        "selection_policy": "maximum validation C-index only",
        "selected_configuration": result.selected_configuration.to_dict(),
        "candidate_test_evaluation_count": result.candidate_test_evaluation_count,
        "winner_test_evaluation_count": result.winner_test_evaluation_count,
        "runtime": result.runtime.to_dict(),
        "random_seeds": {},
        "test_risk_sha256": _risk_sha256(test_risk),
    }
    _write_json(bundle / "metadata.json", metadata)
    _write_json(bundle / "metrics.json", _metric_payload(result))
    _write_json(bundle / "feature_contract.json", _contract_payload(result))
    with (bundle / "validation_leaderboard.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(_leaderboard_rows(result)[0]))
        writer.writeheader()
        writer.writerows(_leaderboard_rows(result))
    (bundle / "report.md").write_text(_report(result), encoding="utf-8")
    with (bundle / "preprocessor.pkl").open("wb") as stream:
        pickle.dump(selection.preprocessor, stream, protocol=pickle.HIGHEST_PROTOCOL)
    with (bundle / "cox_model.pkl").open("wb") as stream:
        pickle.dump(selection.model, stream, protocol=pickle.HIGHEST_PROTOCOL)
    refresh_track_b_checksums(bundle)
    if {path.name for path in bundle.iterdir()} != set(_INITIAL_BUNDLE_FILES) | {"checksums.sha256"}:
        raise RuntimeError("Track B artifact bundle is incomplete")
    return bundle


def verify_track_b_reload(
    bundle: Path,
    prepared: PreparedTrackBRun,
) -> TrackBReloadVerification:
    """Reload trusted local objects and verify exact held-out risk bytes and feature order."""
    root = Path(bundle)
    metadata = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
    contract = json.loads((root / "feature_contract.json").read_text(encoding="utf-8"))
    preprocessor = load_trusted_pickle(root / "preprocessor.pkl", trusted=True)
    model = load_trusted_pickle(root / "cox_model.pkl", trusted=True)
    values = np.asarray(preprocessor.transform(prepared.test_predictors), dtype=float)
    names = track_b_feature_names(preprocessor)
    risk_sha256 = _risk_sha256(model.predict_risk(values))
    feature_order_matches = list(names) == contract["model_feature_names"]
    expected_sha256 = metadata["test_risk_sha256"]
    passed = feature_order_matches and risk_sha256 == expected_sha256
    return TrackBReloadVerification(
        passed=passed,
        feature_order_matches=feature_order_matches,
        max_absolute_risk_difference=0.0 if risk_sha256 == expected_sha256 else float("inf"),
        risk_sha256=risk_sha256,
    )
