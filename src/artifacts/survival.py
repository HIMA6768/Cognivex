"""Trusted local persistence for R5 Track A model bundles."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import pickle

from src.contracts import ArtifactRecord, TrackAExperimentResult


_COEFFICIENT_COLUMNS = (
    "feature_name", "coefficient", "hazard_ratio", "standard_error",
    "coefficient_ci_lower_95", "coefficient_ci_upper_95",
    "hazard_ratio_ci_lower_95", "hazard_ratio_ci_upper_95", "z_statistic", "p_value",
)
_PH_COLUMNS = ("feature_name", "test_statistic", "p_value", "flagged")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_csv(path: Path, columns: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_track_a_artifacts(
    preprocessor,
    model,
    result: TrackAExperimentResult,
    output_root: Path,
) -> tuple[ArtifactRecord, ...]:
    """Write one non-overwriting R5 bundle; pickle objects remain local and trusted."""
    if not isinstance(result, TrackAExperimentResult):
        raise TypeError("result must be a TrackAExperimentResult")
    bundle = Path(output_root) / result.experiment_id
    if bundle.exists() and any(bundle.iterdir()):
        raise FileExistsError(f"experiment bundle already exists: {bundle}")
    bundle.mkdir(parents=True, exist_ok=True)

    payload = result.to_dict()
    (bundle / "experiment.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    metrics = {
        "train": result.train_metric.to_dict(),
        "validation": result.validation_metric.to_dict(),
        "held_out_test": {
            "row_count": result.held_out_test_count,
            "transformed": result.test_transformed,
            "predicted": result.test_predicted,
            "scored": result.test_scored,
        },
    }
    (bundle / "metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_csv(bundle / "coefficients.csv", _COEFFICIENT_COLUMNS, [item.to_dict() for item in result.coefficients])
    _write_csv(bundle / "ph_diagnostics.csv", _PH_COLUMNS, [item.to_dict() for item in result.ph_diagnostics.features])
    with (bundle / "preprocessor.pkl").open("wb") as stream:
        pickle.dump(preprocessor, stream, protocol=pickle.HIGHEST_PROTOCOL)
    with (bundle / "cox_model.pkl").open("wb") as stream:
        pickle.dump(model, stream, protocol=pickle.HIGHEST_PROTOCOL)

    names = (
        "experiment.json", "metrics.json", "coefficients.csv", "ph_diagnostics.csv",
        "preprocessor.pkl", "cox_model.pkl",
    )
    records = tuple(
        ArtifactRecord(
            name=name,
            relative_path=(Path(result.experiment_id) / name).as_posix(),
            sha256=_sha256(bundle / name),
            trusted_binary=name.endswith(".pkl"),
        )
        for name in names
    )
    (bundle / "checksums.sha256").write_text(
        "".join(f"{record.sha256}  {record.name}\n" for record in records),
        encoding="utf-8",
    )
    return records


def load_trusted_pickle(path: Path, *, trusted: bool = False):
    """Load only an explicitly trusted local pickle artifact."""
    if not trusted:
        raise PermissionError("pickle loading requires trusted=True for a verified local artifact")
    with Path(path).open("rb") as stream:
        return pickle.load(stream)
