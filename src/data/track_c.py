"""Canonical Track C feature loading, target eligibility, and cohort ordering."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

import pandas as pd

from src.contracts import TrackCExclusionSummary, TrackCFeatureContract
from src.data.engineer_compatibility import parse_selected_features
from src.data.metabric import MetabricPaths
from src.preprocessing.schema import load_preprocessing_schema


TRACK_C_TARGET_COLUMN = "pam50_+_claudin-low_subtype"
TRACK_C_CLASS_ORDER = ("Basal", "Her2", "LumA", "LumB", "Normal", "claudin-low")
TRACK_C_EXCLUDED_LABELS = ("NC",)
DEFAULT_SELECTED_FEATURES = Path("ai_handoff_data/v1/selected_features.txt")
LOCKED_SPLITS = ("train", "validation", "test")


@dataclass(frozen=True, slots=True)
class OrderedTrackCSplit:
    """One eligible split in canonical manifest order."""

    split: str
    patient_ids: tuple[str, ...]
    predictors: pd.DataFrame
    targets: pd.Series
    exclusions: TrackCExclusionSummary
    fingerprint: str

    @property
    def row_count(self) -> int:
        return len(self.patient_ids)


@dataclass(frozen=True, slots=True)
class TrackCOrderedCohorts:
    """All locked Track C splits after target-only eligibility filtering."""

    train: OrderedTrackCSplit
    validation: OrderedTrackCSplit
    test: OrderedTrackCSplit

    @property
    def splits(self) -> tuple[OrderedTrackCSplit, ...]:
        return self.train, self.validation, self.test


def load_track_c_feature_contract(
    repository_root: Path,
    *,
    selected_features_path: Path | None = None,
) -> TrackCFeatureContract:
    """Load the explicit 68-feature contract without dynamic feature discovery."""
    root = Path(repository_root).resolve()
    schema = load_preprocessing_schema(MetabricPaths.from_repository_root(root))
    selected = parse_selected_features(selected_features_path or root / DEFAULT_SELECTED_FEATURES)
    contract = TrackCFeatureContract(
        expression_features=selected.expression_features,
        mutation_features=selected.mutation_features,
    )
    missing = tuple(
        name
        for name in contract.expression_features
        if name not in schema.mrna_features
    ) + tuple(
        name
        for name in contract.mutation_features
        if name not in schema.mutation_features
    )
    if missing:
        raise ValueError(
            "selected Track C features are absent from canonical metadata: "
            + ", ".join(missing)
        )
    return contract


def ordered_patient_fingerprint(patient_ids: tuple[str, ...]) -> str:
    """Hash an already canonicalized unique patient sequence."""
    if len(patient_ids) != len(set(patient_ids)):
        raise ValueError("patient IDs must be unique before fingerprinting")
    return hashlib.sha256("\n".join(patient_ids).encode("utf-8")).hexdigest()


def _validate_inputs(
    prepared: pd.DataFrame,
    manifest: pd.DataFrame,
    contract: TrackCFeatureContract,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    required_prepared = {"patient_id", TRACK_C_TARGET_COLUMN, *contract.raw_features}
    required_manifest = {"patient_id", "split"}
    missing_prepared = sorted(required_prepared.difference(prepared.columns))
    missing_manifest = sorted(required_manifest.difference(manifest.columns))
    if missing_prepared:
        raise ValueError("prepared data is missing Track C columns: " + ", ".join(missing_prepared))
    if missing_manifest:
        raise ValueError("manifest is missing columns: " + ", ".join(missing_manifest))
    prepared_copy = prepared.copy(deep=True)
    manifest_copy = manifest.copy(deep=True)
    prepared_copy["patient_id"] = prepared_copy["patient_id"].astype(str)
    manifest_copy["patient_id"] = manifest_copy["patient_id"].astype(str)
    if prepared_copy["patient_id"].duplicated().any():
        raise ValueError("prepared patient IDs must be unique")
    if manifest_copy["patient_id"].duplicated().any():
        raise ValueError("manifest patient IDs must be unique")
    if set(prepared_copy["patient_id"]) != set(manifest_copy["patient_id"]):
        raise ValueError("prepared and manifest patient IDs must match exactly")
    if not manifest_copy["split"].isin(LOCKED_SPLITS).all():
        raise ValueError("manifest contains an unsupported split")
    return prepared_copy, manifest_copy


def load_ordered_track_c_cohorts(
    prepared: pd.DataFrame,
    manifest: pd.DataFrame,
    *,
    contract: TrackCFeatureContract,
) -> TrackCOrderedCohorts:
    """Apply Track-C-only target eligibility in canonical manifest order."""
    source, locked = _validate_inputs(prepared, manifest, contract)
    source_by_id = source.set_index("patient_id", drop=False)
    ordered = source_by_id.loc[locked["patient_id"]].copy()
    ordered["split"] = locked["split"].to_numpy(copy=True)
    results: dict[str, OrderedTrackCSplit] = {}
    for split in LOCKED_SPLITS:
        split_frame = ordered.loc[ordered["split"].eq(split)].copy()
        target = split_frame[TRACK_C_TARGET_COLUMN]
        missing = target.isna() | target.astype("string").str.strip().eq("").fillna(False)
        nc = target.eq("NC") & ~missing
        supported = target.isin(TRACK_C_CLASS_ORDER)
        unsupported = ~missing & ~nc & ~supported
        eligible = supported & ~missing & ~nc
        eligible_frame = split_frame.loc[eligible]
        patient_ids = tuple(eligible_frame["patient_id"].astype(str))
        predictor_frame = eligible_frame.loc[:, list(contract.raw_features)].copy()
        predictor_frame.index = pd.Index(patient_ids, name="patient_id")
        targets = eligible_frame[TRACK_C_TARGET_COLUMN].astype(str).copy()
        targets.index = predictor_frame.index
        exclusions = TrackCExclusionSummary(
            split=split,
            source_rows=len(split_frame),
            eligible_rows=len(eligible_frame),
            nc=int(nc.sum()),
            missing=int(missing.sum()),
            unsupported=int(unsupported.sum()),
        )
        results[split] = OrderedTrackCSplit(
            split=split,
            patient_ids=patient_ids,
            predictors=predictor_frame,
            targets=targets,
            exclusions=exclusions,
            fingerprint=ordered_patient_fingerprint(patient_ids),
        )
    return TrackCOrderedCohorts(
        train=results["train"],
        validation=results["validation"],
        test=results["test"],
    )
