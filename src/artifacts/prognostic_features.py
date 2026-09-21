"""Checksum-gated trusted loading for the frozen R6 Track B source."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.metadata import version
import json
from pathlib import Path
import subprocess
from typing import Mapping

from lifelines import CoxPHFitter
from sklearn.pipeline import Pipeline

from src.artifacts.checksums import manifest_digest_matches, sha256_file
from src.modeling.track_b import PenalizedCoxPHAdapter
from src.preprocessing.track_b import track_b_feature_names
from src.contracts import (
    COEF_EPS,
    FEATURE_EFFECTS_CSV_COLUMNS,
    PrognosticFeatureAnalysisResult,
)

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
R6_FROZEN_SOURCE_FILES = (
    "src/training/track_b.py",
    "src/modeling/track_b.py",
    "src/artifacts/track_b.py",
    "src/preprocessing/track_b.py",
    "scripts/train_track_b.py",
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


@dataclass(frozen=True, slots=True)
class PrognosticFeatureBundleVerification:
    """Read-only aggregate verification result for one R8 bundle."""

    passed: bool
    checks: Mapping[str, bool]


def _sha256(path: Path) -> str:
    return sha256_file(path)


def _read_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return payload


def _frozen_commit_is_available(root: Path) -> bool:
    return subprocess.run(
        ["git", "cat-file", "-e", f"{R6_FROZEN_COMMIT}^{{commit}}"],
        cwd=root,
        capture_output=True,
        check=False,
    ).returncode == 0


def verify_frozen_r6_tracked_state(repository_root: Path) -> None:
    """Protect frozen R6 sources while allowing shallow deployment checkouts.

    The checksum manifest protects the exact artifact payload.  When the
    historic R6 commit is locally available, the dedicated R6 source and
    textual trust-anchor files must additionally match it.  Deployment clones
    may be shallow; absence of that historical Git object is not source drift.
    """
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
    if not _frozen_commit_is_available(root):
        return
    unchanged = subprocess.run(
        ["git", "diff", "--quiet", R6_FROZEN_COMMIT, "--", *relative_paths, *R6_FROZEN_SOURCE_FILES],
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
    actual_files = {path.name for path in root.iterdir() if path.is_file()}
    if actual_files != R6_CHECKSUM_FILES | {"checksums.sha256"}:
        raise ValueError("R6 bundle contains an unexpected file")
    for name, expected in digests.items():
        path = root / name
        if not path.is_file() or not manifest_digest_matches(path, expected):
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


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git_commit(repository_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=Path(repository_root),
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _float_text(value: float) -> str:
    return format(float(value), ".17g")


def _effect_row(effect) -> dict[str, object]:
    summary = effect.model_summary
    return {
        "rank": str(effect.rank),
        "frozen_genomic_order": str(effect.frozen_genomic_order),
        "raw_feature_name": effect.raw_feature_name,
        "model_feature_name": effect.model_feature_name,
        "feature_type": effect.feature_type.value,
        "beta": _float_text(effect.beta),
        "abs_beta": _float_text(effect.abs_beta),
        "hazard_ratio": _float_text(effect.hazard_ratio),
        "direction": effect.direction.value,
        "direction_display": effect.direction_display,
        "is_active": "true" if effect.is_active else "false",
        "standard_error": _float_text(summary.standard_error),
        "beta_ci_lower_95": _float_text(summary.beta_ci_lower_95),
        "beta_ci_upper_95": _float_text(summary.beta_ci_upper_95),
        "hazard_ratio_ci_lower_95": _float_text(summary.hazard_ratio_ci_lower_95),
        "hazard_ratio_ci_upper_95": _float_text(summary.hazard_ratio_ci_upper_95),
        "comparison_to": _float_text(summary.comparison_to),
        "z_statistic": _float_text(summary.z_statistic),
        "p_value": _float_text(summary.p_value),
        "negative_log2_p_value": _float_text(summary.negative_log2_p_value),
    }


def _summarize(result: PrognosticFeatureAnalysisResult) -> dict[str, object]:
    from src.analysis.prognostic_features import summarize_prognostic_feature_effects

    return summarize_prognostic_feature_effects(result)


def _metadata_payload(
    result: PrognosticFeatureAnalysisResult,
    source: VerifiedTrackBSource,
) -> dict[str, object]:
    dataset = source.metadata["dataset"]
    source_runtime = source.metadata["runtime"]
    selected = source.metadata["selected_configuration"]
    genomic_mapping = [
        {
            "frozen_genomic_order": effect.frozen_genomic_order,
            "raw_feature_name": effect.raw_feature_name,
            "model_feature_name": effect.model_feature_name,
            "feature_type": effect.feature_type.value,
        }
        for effect in sorted(result.effects, key=lambda item: item.frozen_genomic_order)
    ]
    return {
        "schema_version": result.schema_version,
        "analysis_id": result.analysis_id,
        "generated_at_utc": _utc_now(),
        "source": {
            "track": "R6 Track B",
            "experiment_id": source.metadata["experiment_id"],
            "bundle_path": R6_BUNDLE_RELATIVE.as_posix(),
            "frozen_implementation_commit": R6_FROZEN_COMMIT,
            "artifact_generation_commit": source_runtime["git_commit"],
            "hashes": {
                "cox_model.pkl": source.verified_digests["cox_model.pkl"],
                "preprocessor.pkl": source.verified_digests["preprocessor.pkl"],
                "feature_contract.json": source.verified_digests["feature_contract.json"],
                "metadata.json": source.verified_digests["metadata.json"],
                "checksums.sha256": _sha256(source.bundle / "checksums.sha256"),
            },
            "prepared_path": dataset["prepared_path"],
            "prepared_sha256": dataset["prepared_sha256"],
            "manifest_path": dataset["manifest_path"],
            "manifest_sha256": dataset["manifest_sha256"],
        },
        "model": {
            "adapter_class": type(source.model).__name__,
            "fitter_class": type(source.model.fitter).__name__,
            "baseline_estimation_method": source.model.fitter.baseline_estimation_method,
            "penalizer": selected["penalizer"],
            "l1_ratio": selected["l1_ratio"],
            "alpha": source.model.fitter.alpha,
        },
        "feature_contract": {
            "encoded_r6_total": 80,
            "excluded_clinical": 12,
            "analyzed_total": 68,
            "expression": 50,
            "mutation_presence": 18,
            "clinical": 0,
            "genomic_mapping": genomic_mapping,
        },
        "coefficient_contract": {
            "coef_eps": result.coef_eps,
            "activity_rule": "abs(beta) > COEF_EPS",
            "direction_rule": "higher if beta > COEF_EPS; lower if beta < -COEF_EPS; otherwise effectively zero",
            "ranking_rule": "descending abs_beta, then frozen_genomic_order",
            "inferential_fields": "model-reported descriptive values only; never used for selection, filtering, activity, direction, or ranking",
        },
        "serialization": {
            "float": ".17g round-trip-safe text",
            "json": "UTF-8, sorted keys, indent 2, finite only, LF, trailing newline",
            "csv": "UTF-8, fixed 20-column order, LF, trailing newline",
        },
        "runtime": {
            "generation_git_commit": _git_commit(source.repository_root),
            "python": source_runtime["python_version"],
            "lifelines": version("lifelines"),
            "pandas": version("pandas"),
            "numpy": version("numpy"),
            "scikit_learn": version("scikit-learn"),
        },
    }


def render_prognostic_feature_report(
    result: PrognosticFeatureAnalysisResult,
    metadata: Mapping[str, object],
) -> str:
    """Render the full aggregate coefficient table with explicit scientific limits."""
    source = metadata.get("source", {})
    experiment_id = source.get("experiment_id", "r6-track-b-v1") if isinstance(source, Mapping) else "r6-track-b-v1"
    summary = _summarize(result)
    rows = "\n".join(
        f"| {effect.rank} | {effect.raw_feature_name} | {effect.feature_type.value} | "
        f"{_float_text(effect.beta)} | {_float_text(effect.hazard_ratio)} | "
        f"{effect.direction_display} | {'yes' if effect.is_active else 'no'} |"
        for effect in result.effects
    )
    return f"""# R8 Prognostic Genomic Feature Analysis

## Boundary and source

This research-only analysis reports model-associated coefficients from the frozen R6 Track B experiment `{experiment_id}`. It does not fit, tune, select, or retrain a model and does not establish causality or clinical utility.

## Method

- All {summary['total']} genomic predictors are retained: 50 expression and 18 mutation-presence features.
- Activity uses the numerical rule `abs(beta) > {result.coef_eps}`.
- Rank uses descending absolute beta, followed by frozen genomic order for exact ties.
- Model-reported intervals and p-values are descriptive only and do not control rank, activity, filtering, or emphasis.

## Complete model-associated feature table

| Rank | Raw feature | Type | Beta | Hazard ratio | Direction | Active |
|---:|---|---|---:|---:|---|---|
{rows}

## Interpretation limitations

An expression beta is the modeled association per one training-standardized expression unit, conditional on the other Track B predictors. A mutation beta is the modeled association for mutation presence versus absence; mutation inputs are unscaled binary indicators. Comparing absolute coefficients across these feature types is a model-scale association ranking, not biological unit equivalence.

These outputs do not establish causality, disease mechanisms, biomarkers, or treatment effects. They are descriptive outputs from one penalized Cox model and require external validation.
"""


def refresh_prognostic_feature_checksums(bundle: Path) -> None:
    """Write sorted SHA-256 values for every bundle file except the manifest itself."""
    root = Path(bundle)
    names = sorted(path.name for path in root.iterdir() if path.name != "checksums.sha256")
    (root / "checksums.sha256").write_text(
        "".join(f"{_sha256(root / name)}  {name}\n" for name in names),
        encoding="utf-8",
        newline="\n",
    )


def write_prognostic_feature_bundle(
    result: PrognosticFeatureAnalysisResult,
    source: VerifiedTrackBSource,
    output_root: Path,
) -> Path:
    """Persist one non-overwriting, aggregate-only pre-audit R8 bundle."""
    if not isinstance(result, PrognosticFeatureAnalysisResult):
        raise TypeError("result must be PrognosticFeatureAnalysisResult")
    bundle = Path(output_root) / result.analysis_id
    if bundle.exists():
        raise FileExistsError(f"analysis bundle already exists: {bundle}")
    bundle.mkdir(parents=True)
    metadata = _metadata_payload(result, source)
    with (bundle / "feature_effects.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=list(FEATURE_EFFECTS_CSV_COLUMNS),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(_effect_row(effect) for effect in result.effects)
    summary = {
        "schema_version": result.schema_version,
        "analysis_id": result.analysis_id,
        "status": "COMPLETE",
        "coef_eps": result.coef_eps,
        **_summarize(result),
    }
    _write_json(bundle / "metadata.json", metadata)
    _write_json(bundle / "summary.json", summary)
    (bundle / "report.md").write_text(
        render_prognostic_feature_report(result, metadata),
        encoding="utf-8",
        newline="\n",
    )
    refresh_prognostic_feature_checksums(bundle)
    expected = {
        "feature_effects.csv",
        "metadata.json",
        "summary.json",
        "report.md",
        "checksums.sha256",
    }
    if {path.name for path in bundle.iterdir()} != expected:
        raise RuntimeError("pre-audit R8 bundle has an unexpected file set")
    return bundle


def _hash_tree(path: Path) -> dict[str, str]:
    return {
        item.name: _sha256(item)
        for item in sorted(Path(path).iterdir(), key=lambda value: value.name)
        if item.is_file()
    }


def _verify_bundle_checksums(bundle: Path) -> bool:
    root = Path(bundle)
    manifest = root / "checksums.sha256"
    if not manifest.is_file():
        return False
    try:
        entries = {}
        for line in manifest.read_text(encoding="utf-8").splitlines():
            digest, name = line.split("  ", maxsplit=1)
            if name in entries or len(digest) != 64:
                return False
            entries[name] = digest
    except (OSError, ValueError):
        return False
    expected_names = {path.name for path in root.iterdir() if path.is_file() and path.name != "checksums.sha256"}
    return set(entries) == expected_names and all(
        (root / name).is_file() and manifest_digest_matches(root / name, digest)
        for name, digest in entries.items()
    )


def _without_volatile_metadata(payload: Mapping[str, object]) -> dict[str, object]:
    clone = json.loads(json.dumps(payload))
    clone.pop("generated_at_utc", None)
    runtime = clone.get("runtime")
    if isinstance(runtime, dict):
        runtime.pop("generation_git_commit", None)
    return clone


def verify_prognostic_feature_bundle(
    bundle: Path,
    r6_bundle: Path,
    repository_root: Path,
) -> PrognosticFeatureBundleVerification:
    """Recompute R8 evidence in memory and verify persistence without writing."""
    from src.analysis.prognostic_features import (
        build_genomic_feature_mapping,
        extract_prognostic_feature_effects,
        validate_genomic_mapping_authorities,
    )

    root = Path(bundle).resolve()
    source_root = Path(r6_bundle).resolve()
    before_r6 = _hash_tree(source_root)
    before_r8 = _hash_tree(root)
    checks: dict[str, bool] = {
        "file_set": False,
        "checksums": False,
        "effects_match": False,
        "summary_match": False,
        "report_match": False,
        "lineage_match": False,
        "source_unchanged": False,
        "bundle_unchanged": False,
    }
    try:
        source = verify_and_load_track_b_source(source_root, repository_root)
        mapping = build_genomic_feature_mapping(source.feature_contract, source.model_feature_names)
        validate_genomic_mapping_authorities(mapping, source)
        recomputed = extract_prognostic_feature_effects(source, mapping)
        names = {path.name for path in root.iterdir() if path.is_file()}
        pre_audit = {
            "feature_effects.csv",
            "metadata.json",
            "summary.json",
            "report.md",
            "checksums.sha256",
        }
        final = pre_audit | {"audit.json"}
        checks["file_set"] = names in (pre_audit, final)
        checks["checksums"] = _verify_bundle_checksums(root)

        with (root / "feature_effects.csv").open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            persisted_rows = list(reader)
        checks["effects_match"] = (
            tuple(reader.fieldnames or ()) == FEATURE_EFFECTS_CSV_COLUMNS
            and persisted_rows == [_effect_row(effect) for effect in recomputed.effects]
        )
        persisted_summary = _read_json(root / "summary.json")
        expected_summary = {
            "schema_version": recomputed.schema_version,
            "analysis_id": recomputed.analysis_id,
            "status": "COMPLETE",
            "coef_eps": recomputed.coef_eps,
            **_summarize(recomputed),
        }
        checks["summary_match"] = persisted_summary == expected_summary

        persisted_metadata = _read_json(root / "metadata.json")
        timestamp = persisted_metadata.get("generated_at_utc")
        runtime = persisted_metadata.get("runtime")
        generation_commit = runtime.get("generation_git_commit") if isinstance(runtime, dict) else None
        syntax_valid = isinstance(timestamp, str) and isinstance(generation_commit, str) and bool(generation_commit)
        if syntax_valid:
            try:
                datetime.fromisoformat(timestamp)
            except ValueError:
                syntax_valid = False
        expected_metadata = _metadata_payload(recomputed, source)
        checks["lineage_match"] = syntax_valid and (
            _without_volatile_metadata(persisted_metadata)
            == _without_volatile_metadata(expected_metadata)
        )
        checks["report_match"] = (
            (root / "report.md").read_text(encoding="utf-8")
            == render_prognostic_feature_report(recomputed, persisted_metadata)
        )
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError, csv.Error):
        pass
    finally:
        checks["source_unchanged"] = before_r6 == _hash_tree(source_root)
        checks["bundle_unchanged"] = before_r8 == _hash_tree(root)
    return PrognosticFeatureBundleVerification(passed=all(checks.values()), checks=checks)
