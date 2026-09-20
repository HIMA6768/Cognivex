"""Canonical checksum-gated artifact registry for R9 runtime inference."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from sklearn.pipeline import Pipeline

from src.artifacts.prognostic_features import verify_and_load_track_b_source
from src.artifacts.survival import load_trusted_pickle
from src.artifacts.track_c import verify_track_c_checksums
from src.contracts.inference import AnalysisTrack
from src.modeling.survival import LifelinesCoxPHAdapter


R5_BUNDLE = Path("artifacts/models/track_a/r5a-track-a-baseline-v1")
R6_BUNDLE = Path("artifacts/models/track_b/r6-track-b-v1")
R7_BUNDLE = Path("artifacts/models/track_c/r7-track-c-v1")
R8_BUNDLE = Path("artifacts/analysis/r8-prognostic-features-v1")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _checksums(bundle: Path) -> dict[str, str]:
    manifest = bundle / "checksums.sha256"
    if not manifest.is_file():
        raise ValueError("checksum manifest is missing")
    rows = [line.split("  ", 1) for line in manifest.read_text(encoding="utf-8").splitlines() if line]
    if any(len(row) != 2 or len(row[0]) != 64 for row in rows):
        raise ValueError("checksum manifest is malformed")
    entries = {name: digest for digest, name in rows}
    expected = {path.name for path in bundle.iterdir() if path.is_file() and path.name != "checksums.sha256"}
    if set(entries) != expected or any(_sha256(bundle / name) != digest for name, digest in entries.items()):
        raise ValueError("checksum verification failed")
    return entries


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
    if not verify_track_c_checksums(bundle):
        raise ValueError("R7 checksum verification failed")
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
        except Exception:
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
