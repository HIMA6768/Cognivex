"""Non-overwriting R7 artifacts and read-only trusted reload verification."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import pickle
from typing import Any, TYPE_CHECKING

import numpy as np

from src.data import TRACK_C_CLASS_ORDER, ordered_patient_fingerprint
from src.evaluation.classification import (
    evaluate_classification,
    prediction_digest,
    probability_digest,
    reorder_and_validate_probabilities,
)

from .survival import load_trusted_pickle

if TYPE_CHECKING:
    from src.contracts import TrackCExperimentResult
    from src.training.track_c import PreparedTrackCRun, PreparedTrackCTest, SelectedTrackCModel


REQUIRED_TRACK_C_FILES = {
    "pipeline.pkl",
    "validation_leaderboard.csv",
    "metrics.json",
    "metadata.json",
    "feature_contract.json",
    "confusion_matrix.csv",
    "classification_report.json",
    "report.md",
    "checksums.sha256",
}


@dataclass(frozen=True, slots=True)
class TrackCReloadVerification:
    passed: bool
    prediction_digest_matches: bool
    probability_digest_matches: bool
    metrics_match: bool
    confusion_matrix_matches: bool
    feature_order_matches: bool
    class_order_matches: bool
    probability_normalized: bool


@dataclass(frozen=True, slots=True)
class TrackCBundleVerification:
    passed: bool
    checks: dict[str, bool]
    reload: TrackCReloadVerification


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _feature_payload(result: TrackCExperimentResult) -> dict[str, Any]:
    contract = result.feature_contract
    return {
        "clinical_feature_count": 0,
        "clinical_features": [],
        "expression_feature_count": len(contract.expression_features),
        "expression_features": list(contract.expression_features),
        "mutation_feature_count": len(contract.mutation_features),
        "mutation_features": list(contract.mutation_features),
        "raw_feature_count": len(contract.raw_features),
        "raw_feature_names": list(contract.raw_features),
        "model_feature_count": len(result.model_feature_names),
        "model_feature_names": list(result.model_feature_names),
        "class_order": list(result.class_order),
    }


def _metric_payload(result: TrackCExperimentResult) -> dict[str, Any]:
    return {
        "validation": result.validation_metrics.to_dict(),
        "test": result.test_metrics.to_dict(),
        "test_prediction_digest": result.test_prediction_digest,
        "test_probability_digest": result.test_probability_digest,
        "test_probability_row_count": result.test_probability_row_count,
        "test_probability_normalized": result.test_probability_normalized,
    }


def _leaderboard_rows(result: TrackCExperimentResult) -> list[dict[str, Any]]:
    return [
        {
            "candidate_order": index,
            "key": row.definition.key,
            "display_name": row.definition.display_name,
            "macro_f1": row.validation_metrics.macro_f1,
            "weighted_f1": row.validation_metrics.weighted_f1,
            "accuracy": row.validation_metrics.accuracy,
            "balanced_accuracy": row.validation_metrics.balanced_accuracy,
        }
        for index, row in enumerate(result.leaderboard, start=1)
    ]


def render_track_c_report(
    result: TrackCExperimentResult,
    metadata: dict[str, Any],
) -> str:
    """Render deterministic aggregate R7 evidence without timestamps or row data."""
    rows = _leaderboard_rows(result)
    leaderboard = "\n".join(
        f"| {row['candidate_order']} | {row['display_name']} | {row['macro_f1']:.6f} | "
        f"{row['weighted_f1']:.6f} | {row['accuracy']:.6f} | {row['balanced_accuracy']:.6f} |"
        for row in rows
    )
    test = result.test_metrics
    per_class = "\n".join(
        f"| {item.label} | {item.precision:.6f} | {item.recall:.6f} | {item.f1:.6f} | {item.support} |"
        for item in test.per_class
    )
    confusion = "\n".join(
        "| " + label + " | " + " | ".join(str(value) for value in row) + " |"
        for label, row in zip(result.class_order, test.confusion_matrix, strict=True)
    )
    cohorts = metadata["cohorts"]
    return f"""# R7 Track C — Molecular Subtype Classification

## Objective

Classify six dataset-confirmed molecular subtype labels from the frozen 68-feature genomic contract. The selected model is **{result.selected_definition.display_name}** (`{result.selected_definition.key}`) because it achieved the highest validation Macro-F1 under the approved deterministic tie rule.

## Dataset and eligibility

- Target: `pam50_+_claudin-low_subtype`
- Train: {cohorts['train']['eligible_rows']} eligible; {cohorts['train']['exclusions']['nc']} NC excluded
- Validation: {cohorts['validation']['eligible_rows']} eligible; {cohorts['validation']['exclusions']['nc']} NC excluded
- Test: {cohorts['test']['eligible_rows']} eligible; {cohorts['test']['exclusions']['nc']} NC excluded
- NC, missing targets, and unsupported targets are excluded only from Track C.

## Contract

- Expression predictors: 50
- Mutation-presence predictors: 18, derived with existing R4D annotation semantics
- Clinical predictors: 0
- Target classes: {', '.join(result.class_order)}
- NC, missing targets, and unsupported targets are excluded only from Track C.

## Validation leaderboard

| Order | Model | Macro F1 | Weighted F1 | Accuracy | Balanced accuracy |
|---:|---|---:|---:|---:|---:|
{leaderboard}

## Final frozen-winner test metrics

- Macro F1: {test.macro_f1:.6f}
- Weighted F1: {test.weighted_f1:.6f}
- Accuracy: {test.accuracy:.6f}
- Balanced accuracy: {test.balanced_accuracy:.6f}

### Per-class test metrics

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
{per_class}

### Confusion matrix

Rows are actual classes and columns are predicted classes in the frozen order.

| Actual \\ Predicted | {' | '.join(result.class_order)} |
|---|{'|'.join('---:' for _ in result.class_order)}|
{confusion}

The test set was not used for model selection. Only the frozen validation winner received final test evaluation.

## Limitations

- This is a research/educational prototype, not a diagnostic or clinical decision system.
- Results are specific to the locked internal METABRIC split and require external validation.
- Classification performance does not establish biological causality or feature importance.
"""


def refresh_track_c_checksums(bundle: Path) -> None:
    """Write checksums after bundle creation; never called by read-only verification."""
    root = Path(bundle)
    names = sorted(path.name for path in root.iterdir() if path.name != "checksums.sha256")
    (root / "checksums.sha256").write_text(
        "".join(f"{_sha256(root / name)}  {name}\n" for name in names),
        encoding="utf-8",
    )


def verify_track_c_checksums(bundle: Path) -> bool:
    """Read and verify every declared bundle checksum without writing."""
    root = Path(bundle)
    checksum_path = root / "checksums.sha256"
    if not checksum_path.is_file():
        return False
    declared: dict[str, str] = {}
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) != 2 or len(parts[0]) != 64 or parts[1] in declared:
            return False
        declared[parts[1]] = parts[0]
    expected = REQUIRED_TRACK_C_FILES - {"checksums.sha256"}
    return set(declared) == expected and all(
        (root / name).is_file() and _sha256(root / name) == digest
        for name, digest in declared.items()
    )


def write_track_c_artifacts(
    selection: SelectedTrackCModel,
    result: TrackCExperimentResult,
    run: PreparedTrackCRun,
    output_root: Path,
) -> Path:
    """Persist one aggregate R7 bundle and trusted local pipeline without overwrite."""
    if selection.contract != result.feature_contract or selection.contract != run.selection.contract:
        raise ValueError("Track C feature contracts do not agree")
    bundle = Path(output_root) / result.experiment_id
    if bundle.exists():
        raise FileExistsError(f"experiment bundle already exists: {bundle}")
    bundle.mkdir(parents=True)
    cohorts = {}
    for split in (*run.selection.splits, run.test.split):
        cohorts[split.split] = {
            "source_rows": split.exclusions.source_rows,
            "eligible_rows": split.exclusions.eligible_rows,
            "exclusions": {
                "nc": split.exclusions.nc,
                "missing": split.exclusions.missing,
                "unsupported": split.exclusions.unsupported,
            },
            "cohort_fingerprint": split.fingerprint,
        }
    metadata = {
        "schema_version": result.schema_version,
        "experiment_id": result.experiment_id,
        "track": "C",
        "task": "molecular_subtype_classification",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "prepared_path": "data/metabric/prepared/METABRIC_prepared.csv",
            "prepared_sha256": run.prepared_sha256,
            "manifest_path": "data/metabric/metadata/manifest.csv",
            "manifest_sha256": run.manifest_sha256,
            "patient_count": sum(item.exclusions.source_rows for item in (*run.selection.splits, run.test.split)),
            "column_count": 693,
        },
        "cohorts": cohorts,
        "target": "pam50_+_claudin-low_subtype",
        "class_order": list(result.class_order),
        "excluded_labels": ["NC", "missing", "unsupported"],
        "mutation_policy": "existing R4D parser: zero is absent; accepted non-zero annotation is present; invalid input fails",
        "candidate_definitions": [row.definition.to_dict() for row in result.leaderboard],
        "selection": {
            "primary_metric": "validation_macro_f1",
            "tie_tolerance": 1e-12,
            "tie_break": "declaration_order",
            "selected_model": result.selected_definition.key,
            "candidate_test_evaluation_count": result.candidate_test_evaluation_count,
            "winner_test_evaluation_count": result.winner_test_evaluation_count,
        },
        "random_states": {
            row.definition.key: row.definition.parameters["random_state"]
            for row in result.leaderboard
            if "random_state" in row.definition.parameters
        },
    }
    _write_json(bundle / "metadata.json", metadata)
    _write_json(bundle / "metrics.json", _metric_payload(result))
    _write_json(bundle / "feature_contract.json", _feature_payload(result))
    _write_json(bundle / "classification_report.json", result.test_metrics.classification_report)
    rows = _leaderboard_rows(result)
    with (bundle / "validation_leaderboard.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (bundle / "confusion_matrix.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["actual\\predicted", *result.class_order])
        for label, row in zip(result.class_order, result.test_metrics.confusion_matrix, strict=True):
            writer.writerow([label, *row])
    (bundle / "report.md").write_text(
        render_track_c_report(result, metadata),
        encoding="utf-8",
    )
    with (bundle / "pipeline.pkl").open("wb") as stream:
        pickle.dump(selection.pipeline, stream, protocol=pickle.HIGHEST_PROTOCOL)
    refresh_track_c_checksums(bundle)
    if {path.name for path in bundle.iterdir()} != REQUIRED_TRACK_C_FILES:
        raise RuntimeError("Track C artifact bundle is incomplete")
    return bundle


def _ordered_test(test: PreparedTrackCTest):
    split = test.split
    if split.fingerprint != ordered_patient_fingerprint(split.patient_ids):
        raise ValueError("test fingerprint does not match canonical patient order")
    order = list(split.patient_ids)
    return split.predictors.loc[order], split.targets.loc[order]


def _read_confusion(path: Path) -> tuple[tuple[int, ...], ...]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.reader(stream))
    return tuple(tuple(int(value) for value in row[1:]) for row in rows[1:])


def verify_track_c_reload(bundle: Path, test: PreparedTrackCTest) -> TrackCReloadVerification:
    """Reload the trusted local winner and reproduce held-out aggregate evidence."""
    root = Path(bundle)
    metadata = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
    metrics_payload = json.loads((root / "metrics.json").read_text(encoding="utf-8"))
    contract = json.loads((root / "feature_contract.json").read_text(encoding="utf-8"))
    pipeline = load_trusted_pickle(root / "pipeline.pkl", trusted=True)
    predictors, targets = _ordered_test(test)
    predictions = tuple(str(value) for value in pipeline.predict(predictors))
    probability_output = reorder_and_validate_probabilities(
        pipeline.predict_proba(predictors), pipeline.classes_, TRACK_C_CLASS_ORDER
    )
    recomputed = evaluate_classification(
        targets,
        predictions,
        split="test",
        class_order=TRACK_C_CLASS_ORDER,
        cohort_fingerprint=test.split.fingerprint,
    )
    prediction_matches = prediction_digest(predictions) == metrics_payload["test_prediction_digest"]
    probability_matches = probability_digest(probability_output.probabilities) == metrics_payload["test_probability_digest"]
    metrics_match = recomputed.to_dict() == metrics_payload["test"]
    confusion_matches = recomputed.confusion_matrix == _read_confusion(root / "confusion_matrix.csv")
    feature_matches = contract["model_feature_names"] == [
        *contract["expression_features"],
        *(f"{name}_present" for name in contract["mutation_features"]),
    ]
    class_matches = metadata["class_order"] == list(TRACK_C_CLASS_ORDER) == contract["class_order"]
    normalized = np.allclose(probability_output.probabilities.sum(axis=1), 1.0, atol=1e-8, rtol=0)
    checks = (prediction_matches, probability_matches, metrics_match, confusion_matches, feature_matches, class_matches, bool(normalized))
    return TrackCReloadVerification(
        passed=all(checks),
        prediction_digest_matches=prediction_matches,
        probability_digest_matches=probability_matches,
        metrics_match=metrics_match,
        confusion_matrix_matches=confusion_matches,
        feature_order_matches=feature_matches,
        class_order_matches=class_matches,
        probability_normalized=bool(normalized),
    )


def verify_track_c_bundle(bundle: Path, test: PreparedTrackCTest) -> TrackCBundleVerification:
    """Read-only complete-bundle verification; never trains or rewrites files."""
    root = Path(bundle)
    metadata = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
    metrics = json.loads((root / "metrics.json").read_text(encoding="utf-8"))
    with (root / "validation_leaderboard.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    winner = rows[0]
    for row in rows[1:]:
        score = float(row["macro_f1"])
        best = float(winner["macro_f1"])
        if score > best and not math.isclose(score, best, abs_tol=1e-12, rel_tol=0):
            winner = row
    reload = verify_track_c_reload(root, test)
    report = (root / "report.md").read_text(encoding="utf-8")
    checks = {
        "required_files": {path.name for path in root.iterdir()} == REQUIRED_TRACK_C_FILES,
        "checksums": verify_track_c_checksums(root),
        "validation_winner": winner["key"] == metadata["selection"]["selected_model"],
        "selected_model_identity": metadata["selection"]["selected_model"] in report,
        "test_metrics": reload.metrics_match,
        "confusion_matrix": reload.confusion_matrix_matches,
        "class_order": reload.class_order_matches,
        "feature_order": reload.feature_order_matches,
        "prediction_digest": reload.prediction_digest_matches,
        "probability_digest": reload.probability_digest_matches,
        "probability_normalization": reload.probability_normalized,
        "report_metrics_consistency": all(
            f"{metrics['test'][name]:.6f}" in report
            for name in ("macro_f1", "weighted_f1", "accuracy", "balanced_accuracy")
        ),
    }
    return TrackCBundleVerification(passed=all(checks.values()) and reload.passed, checks=checks, reload=reload)
