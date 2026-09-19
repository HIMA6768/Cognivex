"""Checksum-gated trusted loading for the frozen R6 Track B source."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Mapping

from lifelines import CoxPHFitter
from sklearn.pipeline import Pipeline

from src.modeling.track_b import PenalizedCoxPHAdapter
from src.preprocessing.track_b import track_b_feature_names

from .survival import load_trusted_pickle


R6_BUNDLE_RELATIVE = Path("artifacts/models/track_b/r6-track-b-v1")
R6_FROZEN_COMMIT = "49a8414c1aa828c07cfa9f9dd207a2bdf311b078"
R6_CHECKSUM_FILES = frozenset(
    {
        "audit.json",
        "cox_model.pkl",
        "feature_contract.json",
        "metadata.json",
        "metrics.json",
        "preprocessor.pkl",
        "report.md",
        "validation_leaderboard.csv",
    }
)
R6_TRACKED_FILES = tuple(sorted(R6_CHECKSUM_FILES - {"cox_model.pkl", "preprocessor.pkl"})) + (
    "checksums.sha256",
)


@dataclass(frozen=True, slots=True)
class VerifiedTrackBSource:
    """Validated aggregate R6 source objects with no patient-level rows."""

    repository_root: Path
    bundle: Path
    metadata: Mapping[str, object]
    feature_contract: Mapping[str, object]
    verified_digests: Mapping[str, str]
    preprocessor: Pipeline
    model: PenalizedCoxPHAdapter
    model_feature_names: tuple[str, ...]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return payload


def verify_frozen_r6_tracked_state(repository_root: Path) -> None:
    """Require every tracked R6 trust-anchor byte to match the frozen R6 commit."""
    root = Path(repository_root).resolve()
    relative_paths = [(R6_BUNDLE_RELATIVE / name).as_posix() for name in R6_TRACKED_FILES]
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", *relative_paths],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if tracked.returncode != 0:
        raise ValueError("canonical R6 trust-anchor files must remain tracked")
    unchanged = subprocess.run(
        ["git", "diff", "--quiet", R6_FROZEN_COMMIT, "--", *relative_paths],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if unchanged.returncode != 0:
        raise ValueError(f"frozen R6 tracked files differ from {R6_FROZEN_COMMIT}")


def verify_r6_checksums(bundle: Path) -> dict[str, str]:
    """Verify the exact R6 checksum-covered file set before pickle loading."""
    root = Path(bundle)
    manifest = root / "checksums.sha256"
    if not manifest.is_file():
        raise ValueError("R6 checksum manifest is missing")
    digests: dict[str, str] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        parts = line.split("  ", maxsplit=1)
        if len(parts) != 2 or len(parts[0]) != 64:
            raise ValueError("R6 checksum manifest is malformed")
        digest, name = parts
        if name in digests:
            raise ValueError(f"R6 checksum manifest contains duplicate file: {name}")
        digests[name] = digest.lower()
    if set(digests) != R6_CHECKSUM_FILES:
        raise ValueError("R6 checksum manifest does not cover the exact canonical file set")
    for name, expected in digests.items():
        path = root / name
        if not path.is_file() or _sha256(path) != expected:
            raise ValueError(f"R6 checksum verification failed for {name}")
    return digests


def read_and_validate_r6_metadata(path: Path) -> dict[str, object]:
    """Validate frozen R6 identity and model-selection metadata before deserialization."""
    metadata = _read_json(path)
    expected = {
        "schema_version": "1.0",
        "experiment_id": "r6-track-b-v1",
        "track": "B",
        "task": "clinical_genomic_survival",
        "selection_policy": "maximum validation C-index only",
        "candidate_test_evaluation_count": 0,
        "winner_test_evaluation_count": 1,
    }
    for key, value in expected.items():
        if metadata.get(key) != value:
            raise ValueError(f"R6 {key} identity is invalid")
    selected = metadata.get("selected_configuration")
    if not isinstance(selected, dict):
        raise ValueError("R6 selected_configuration is missing")
    if selected.get("penalizer") != 0.05:
        raise ValueError("R6 penalizer must be 0.05")
    if selected.get("l1_ratio") != 0.5:
        raise ValueError("R6 l1_ratio must be 0.5")
    dataset = metadata.get("dataset")
    if not isinstance(dataset, dict) or dataset.get("patient_count") != 1904 or dataset.get("column_count") != 693:
        raise ValueError("R6 dataset identity is invalid")
    survival = metadata.get("survival_contract")
    if not isinstance(survival, dict) or survival != {
        "censored_value": 0,
        "duration_column": "overall_survival_months",
        "event_column": "overall_survival",
        "event_inverted": False,
        "event_observed_value": 1,
    }:
        raise ValueError("R6 survival contract is invalid")
    return metadata


def read_and_validate_r6_contract(path: Path) -> dict[str, object]:
    """Validate exact raw and encoded R6 feature counts and orders."""
    contract = _read_json(path)
    expected_counts = {
        "clinical_feature_count": 7,
        "expression_feature_count": 50,
        "mutation_feature_count": 18,
        "raw_feature_count": 75,
        "model_feature_count": 80,
    }
    for key, value in expected_counts.items():
        if contract.get(key) != value:
            raise ValueError(f"R6 {key} must be {value}")
    list_fields = (
        "clinical_features",
        "expression_features",
        "mutation_features",
        "raw_feature_names",
        "model_feature_names",
    )
    for field in list_fields:
        values = contract.get(field)
        if not isinstance(values, list) or len(values) != len(set(values)):
            raise ValueError(f"R6 {field} must be an ordered unique list")
    raw = contract["clinical_features"] + contract["expression_features"] + contract["mutation_features"]
    if contract["raw_feature_names"] != raw:
        raise ValueError("R6 raw feature order is invalid")
    return contract


def validate_loaded_track_b_source(
    *,
    repository_root: Path,
    bundle: Path,
    metadata: Mapping[str, object],
    feature_contract: Mapping[str, object],
    verified_digests: Mapping[str, str],
    preprocessor: object,
    model: object,
) -> VerifiedTrackBSource:
    """Validate exact object types, fitted state, configuration, and feature order."""
    if not isinstance(preprocessor, Pipeline):
        raise TypeError("R6 preprocessor must be an sklearn Pipeline")
    if not isinstance(model, PenalizedCoxPHAdapter):
        raise TypeError("R6 model must be a PenalizedCoxPHAdapter")
    if model._fitted is not True:
        raise ValueError("R6 PenalizedCoxPHAdapter must be fitted")
    if not isinstance(model.fitter, CoxPHFitter):
        raise TypeError("R6 adapter fitter must be CoxPHFitter")
    fitter = model.fitter
    if fitter.baseline_estimation_method != "breslow":
        raise ValueError("R6 baseline_estimation_method must be breslow")
    if float(fitter.penalizer) != 0.05:
        raise ValueError("R6 fitted penalizer must be 0.05")
    if float(fitter.l1_ratio) != 0.5:
        raise ValueError("R6 fitted l1_ratio must be 0.5")
    if float(fitter.alpha) != 0.05:
        raise ValueError("R6 fitted alpha must be 0.05")
    names = track_b_feature_names(preprocessor)
    expected_names = tuple(feature_contract["model_feature_names"])
    if len(names) != 80 or names != expected_names:
        raise ValueError("R6 fitted preprocessor feature order is invalid")
    if tuple(model.feature_names) != expected_names:
        raise ValueError("R6 adapter feature order is invalid")
    if tuple(fitter.params_.index) != expected_names or tuple(fitter.summary.index) != expected_names:
        raise ValueError("R6 Cox coefficient order is invalid")
    return VerifiedTrackBSource(
        repository_root=Path(repository_root).resolve(),
        bundle=Path(bundle).resolve(),
        metadata=metadata,
        feature_contract=feature_contract,
        verified_digests=verified_digests,
        preprocessor=preprocessor,
        model=model,
        model_feature_names=names,
    )


def verify_and_load_track_b_source(bundle: Path, repository_root: Path) -> VerifiedTrackBSource:
    """Verify the canonical R6 source completely before trusted pickle loading."""
    resolved = Path(bundle).resolve()
    canonical = (Path(repository_root).resolve() / R6_BUNDLE_RELATIVE).resolve()
    if resolved != canonical:
        raise ValueError("R8 source must be the canonical R6 bundle")
    verify_frozen_r6_tracked_state(repository_root)
    digests = verify_r6_checksums(resolved)
    metadata = read_and_validate_r6_metadata(resolved / "metadata.json")
    contract = read_and_validate_r6_contract(resolved / "feature_contract.json")
    preprocessor = load_trusted_pickle(resolved / "preprocessor.pkl", trusted=True)
    model = load_trusted_pickle(resolved / "cox_model.pkl", trusted=True)
    return validate_loaded_track_b_source(
        repository_root=repository_root,
        bundle=resolved,
        metadata=metadata,
        feature_contract=contract,
        verified_digests=digests,
        preprocessor=preprocessor,
        model=model,
    )
