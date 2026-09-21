"""Canonical checksum-gated artifact registry for R9 runtime inference."""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from pathlib import Path
from typing import Any

from sklearn.pipeline import Pipeline

from src.artifacts.checksums import manifest_digest_matches, sha256_file
from src.artifacts.prognostic_features import verify_and_load_track_b_source
from src.artifacts.survival import load_trusted_pickle
from src.contracts.inference import AnalysisTrack
from src.modeling.survival import LifelinesCoxPHAdapter


R5_BUNDLE = Path("artifacts/models/track_a/r5a-track-a-baseline-v1")
R6_BUNDLE = Path("artifacts/models/track_b/r6-track-b-v1")
R7_BUNDLE = Path("artifacts/models/track_c/r7-track-c-v1")
R8_BUNDLE = Path("artifacts/analysis/r8-prognostic-features-v1")


LOGGER = logging.getLogger(__name__)
_TRACK_RUNTIME_FILES: dict[AnalysisTrack, tuple[Path, tuple[str, ...]]] = {
    AnalysisTrack.TRACK_A: (R5_BUNDLE, ("preprocessor.pkl", "cox_model.pkl")),
    AnalysisTrack.TRACK_B: (R6_BUNDLE, ("preprocessor.pkl", "cox_model.pkl")),
    AnalysisTrack.TRACK_C: (R7_BUNDLE, ("pipeline.pkl",)),
}


def _sha256(path: Path) -> str:
    return sha256_file(path)


def _checksums(bundle: Path) -> dict[str, str]:
    manifest = bundle / "checksums.sha256"
    if not manifest.is_file():
        raise ValueError("checksum manifest is missing")
    rows = [line.split("  ", 1) for line in manifest.read_text(encoding="utf-8").splitlines() if line]
    if any(len(row) != 2 or len(row[0]) != 64 for row in rows):
        raise ValueError("checksum manifest is malformed")
    entries = {name: digest for digest, name in rows}
    expected = {path.name for path in bundle.iterdir() if path.is_file() and path.name != "checksums.sha256"}
    if set(entries) != expected or any(
        not manifest_digest_matches(bundle / name, digest) for name, digest in entries.items()
    ):
        raise ValueError("checksum verification failed")
    return entries


def _track_runtime_file_state(root: Path, track: AnalysisTrack) -> dict[str, object]:
    """Return safe file-presence and checksum evidence without loading a model."""
    relative_bundle, names = _TRACK_RUNTIME_FILES[track]
    bundle = root / relative_bundle
    files: dict[str, dict[str, int | bool | None]] = {}
    for name in names:
        path = bundle / name
        exists = path.is_file()
        files[name] = {"exists": exists, "size_bytes": path.stat().st_size if exists else None}
    try:
        _checksums(bundle)
        checksum_verification: dict[str, object] = {"passed": True}
    except Exception as error:
        checksum_verification = {
            "passed": False,
            "exception_class": type(error).__name__,
            "exception_message": str(error),
        }
    return {
        "bundle": relative_bundle.as_posix(),
        "bundle_exists": bundle.is_dir(),
        "files": files,
        "checksum_verification": checksum_verification,
    }


def canonical_artifact_file_state(root: Path) -> dict[str, object]:
    """Return safe expected-file diagnostics for the canonical runtime bundles."""
    resolved_root = Path(root).resolve()
    return {
        track.value: _track_runtime_file_state(resolved_root, track)
        for track in _TRACK_RUNTIME_FILES
    } | {"r8_bundle_exists": (resolved_root / R8_BUNDLE).is_dir()}


def _log_track_load_failure(root: Path, track: AnalysisTrack, error: Exception) -> None:
    """Emit server-only evidence for an isolated canonical track-load failure."""
    LOGGER.exception(
        "[ONCOMAP_TRACK_LOAD_ERROR] track=%s exception_class=%s "
        "exception_message=%s runtime_files=%s",
        track.value.removeprefix("track_").upper(),
        type(error).__name__,
        str(error),
        _track_runtime_file_state(root, track),
    )


@dataclass(frozen=True, slots=True)
class GlobalInputContract:
    raw_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ArtifactEntry:
    track: AnalysisTrack
    required_fields: tuple[str, ...]
    contract_sha256: str
    metadata: dict[str, Any]
    available: bool
    preprocessor: object | None = None
    model: object | None = None
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class AggregateEntry:
    available: bool
    bundle: Path | None
    metadata: dict[str, Any] | None
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class CanonicalArtifactRegistry:
    repository_root: Path
    global_contract: GlobalInputContract
    track_a: ArtifactEntry
    track_b: ArtifactEntry
    track_c: ArtifactEntry
    r8: AggregateEntry

    def entry(self, track: AnalysisTrack) -> ArtifactEntry:
        return {AnalysisTrack.TRACK_A: self.track_a, AnalysisTrack.TRACK_B: self.track_b,
                AnalysisTrack.TRACK_C: self.track_c}[track]


def _canonical(root: Path, relative: Path) -> Path:
    candidate = (root / relative).resolve()
    if candidate != root.resolve() / relative or not candidate.is_dir():
        raise ValueError("canonical artifact bundle is unavailable")
    return candidate


def _r5(root: Path) -> ArtifactEntry:
    bundle = _canonical(root, R5_BUNDLE); digests = _checksums(bundle)
    experiment = json.loads((bundle / "experiment.json").read_text(encoding="utf-8"))
    config = experiment["configuration"]
    fields = tuple(config["clinical_features"] if "clinical_features" in config else (
        "age_at_diagnosis", "tumor_size", "tumor_stage", "lymph_nodes_examined_positive",
        "er_status_measured_by_ihc", "pr_status", "her2_status"))
    names = tuple(config["feature_names"])
    if experiment.get("experiment_id") != "r5a-track-a-baseline-v1" or len(fields) != 7 or len(names) != 12:
        raise ValueError("R5 textual contract is invalid")
    preprocessor = load_trusted_pickle(bundle / "preprocessor.pkl", trusted=True)
    model = load_trusted_pickle(bundle / "cox_model.pkl", trusted=True)
    if not isinstance(model, LifelinesCoxPHAdapter) or tuple(model.feature_names) != names:
        raise ValueError("R5 post-load contract is invalid")
    return ArtifactEntry(AnalysisTrack.TRACK_A, fields, digests["experiment.json"], experiment, True, preprocessor, model)


def _r6(root: Path) -> ArtifactEntry:
    source = verify_and_load_track_b_source(_canonical(root, R6_BUNDLE), root)
    fields = tuple(source.feature_contract["raw_feature_names"])
    return ArtifactEntry(AnalysisTrack.TRACK_B, fields, source.verified_digests["feature_contract.json"], dict(source.metadata), True, source.preprocessor, source.model)


def _r7(root: Path) -> ArtifactEntry:
    bundle = _canonical(root, R7_BUNDLE)
    _checksums(bundle)
    contract = json.loads((bundle / "feature_contract.json").read_text(encoding="utf-8"))
    metadata = json.loads((bundle / "metadata.json").read_text(encoding="utf-8"))
    fields = tuple(contract["raw_feature_names"])
    if len(fields) != 68 or tuple(metadata["class_order"]) != ("Basal", "Her2", "LumA", "LumB", "Normal", "claudin-low"):
        raise ValueError("R7 textual contract is invalid")
    pipeline = load_trusted_pickle(bundle / "pipeline.pkl", trusted=True)
    if not isinstance(pipeline, Pipeline) or not hasattr(pipeline, "classes_"):
        raise ValueError("R7 post-load contract is invalid")
    return ArtifactEntry(AnalysisTrack.TRACK_C, fields, _checksums(bundle)["feature_contract.json"], metadata, True, pipeline, pipeline)


def _r8(root: Path) -> AggregateEntry:
    bundle = _canonical(root, R8_BUNDLE); _checksums(bundle)
    metadata = json.loads((bundle / "metadata.json").read_text(encoding="utf-8"))
    if metadata.get("analysis_id") != "r8-prognostic-features-v1":
        raise ValueError("R8 identity is invalid")
    return AggregateEntry(True, bundle, metadata)


def _unavailable(track: AnalysisTrack) -> ArtifactEntry:
    return ArtifactEntry(track, (), "", {}, False, error_code="ARTIFACT_UNAVAILABLE", error_message="Canonical artifact is unavailable")


def build_canonical_registry(repository_root: Path) -> CanonicalArtifactRegistry:
    root = Path(repository_root).resolve()
    if not (root / ".git").exists():
        raise ValueError("repository root is invalid")
    entries: dict[AnalysisTrack, ArtifactEntry] = {}
    for track, loader in ((AnalysisTrack.TRACK_A, _r5), (AnalysisTrack.TRACK_B, _r6), (AnalysisTrack.TRACK_C, _r7)):
        try:
            entries[track] = loader(root)
        except Exception as error:
            _log_track_load_failure(root, track, error)
            entries[track] = _unavailable(track)
    r6_fields = entries[AnalysisTrack.TRACK_B].required_fields
    r5_r7 = entries[AnalysisTrack.TRACK_A].required_fields + entries[AnalysisTrack.TRACK_C].required_fields
    if len(r6_fields) == 75:
        fields = r6_fields
        if len(r5_r7) == 75 and r5_r7 != fields:
            raise ValueError("GLOBAL_INPUT_CONTRACT_UNAVAILABLE")
    elif len(r5_r7) == 75:
        fields = r5_r7
    else:
        raise ValueError("GLOBAL_INPUT_CONTRACT_UNAVAILABLE")
    try:
        r8 = _r8(root)
    except Exception:
        r8 = AggregateEntry(False, None, None, "ARTIFACT_UNAVAILABLE", "Aggregate analysis artifact is unavailable")
    return CanonicalArtifactRegistry(root, GlobalInputContract(fields), entries[AnalysisTrack.TRACK_A], entries[AnalysisTrack.TRACK_B], entries[AnalysisTrack.TRACK_C], r8)
