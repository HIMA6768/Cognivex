"""Framework-independent R9 analysis and inference contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math
from typing import Literal, Mapping

from .analysis import SerializableContract
from .prognostic_features import PrognosticFeatureEffect

R9_SCHEMA_VERSION = "r9-v1"
PROGNOSIS_OUTPUT_KIND = "log_partial_hazard"
PROGNOSIS_OUTPUT_LABEL = "Model log relative hazard score"
PROGNOSIS_INTERPRETATION = ("Model-relative log partial hazard; not an absolute survival probability, "
    "mortality probability, risk category, treatment recommendation, or clinical prognosis.")
SURVIVAL_ESTIMATE_INTERPRETATION = (
    "Model-estimated survival probability from the frozen METABRIC Cox model. "
    "This is an internal research estimate, not a validated clinical prognosis "
    "or treatment recommendation."
)
FROZEN_SUBTYPE_CLASS_ORDER = ("Basal", "Her2", "LumA", "LumB", "Normal", "claudin-low")


class AnalysisTrack(StrEnum):
    TRACK_A = "track_a"
    TRACK_B = "track_b"
    TRACK_C = "track_c"


class TrackReadinessState(StrEnum):
    READY = "ready"
    MISSING_REQUIRED_FIELDS = "missing_required_fields"
    INVALID_INPUT = "invalid_input"
    ARTIFACT_UNAVAILABLE = "artifact_unavailable"
    INFERENCE_ERROR = "inference_error"


def _text(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")


def _field_names(values: tuple[str, ...], name: str) -> None:
    if not isinstance(values, tuple) or not all(isinstance(value, str) and value for value in values):
        raise ValueError(f"{name} must be a tuple of field names")


@dataclass(frozen=True, slots=True)
class AnalysisRequest(SerializableContract):
    features: Mapping[str, str | int | float | None]
    requested_tracks: tuple[AnalysisTrack, ...] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.features, Mapping):
            raise TypeError("features must be a mapping")
        if self.requested_tracks is not None and not isinstance(self.requested_tracks, tuple):
            raise TypeError("requested_tracks must be a tuple or None")


@dataclass(frozen=True, slots=True)
class ResultLineage(SerializableContract):
    track: AnalysisTrack
    experiment_id: str
    schema_version: str
    contract_artifact_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.track, AnalysisTrack):
            raise TypeError("track must be AnalysisTrack")
        for name in ("experiment_id", "schema_version", "contract_artifact_sha256"):
            _text(getattr(self, name), name)
        if len(self.contract_artifact_sha256) != 64 or any(c not in "0123456789abcdef" for c in self.contract_artifact_sha256):
            raise ValueError("contract_artifact_sha256 must be lowercase SHA-256")


@dataclass(frozen=True, slots=True)
class SurvivalProbabilityEstimates(SerializableContract):
    """Three fixed-horizon estimates from a frozen Cox baseline survival curve."""

    survival_probability_1y: float
    survival_probability_3y: float
    survival_probability_5y: float
    interpretation: str = SURVIVAL_ESTIMATE_INTERPRETATION

    def __post_init__(self) -> None:
        values = (
            self.survival_probability_1y,
            self.survival_probability_3y,
            self.survival_probability_5y,
        )
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1 for value in values):
            raise ValueError("survival probabilities must be finite and bounded in [0, 1]")
        if values[0] < values[1] or values[1] < values[2]:
            raise ValueError("survival probabilities must be non-increasing by horizon")
        if self.interpretation != SURVIVAL_ESTIMATE_INTERPRETATION:
            raise ValueError("survival estimate interpretation is frozen")


@dataclass(frozen=True, slots=True)
class PrognosisResult(SerializableContract):
    lineage: ResultLineage
    output_kind: Literal["log_partial_hazard"]
    output_label: str
    value: float
    interpretation: str
    survival_estimates: SurvivalProbabilityEstimates | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.lineage, ResultLineage):
            raise TypeError("lineage must be ResultLineage")
        if self.output_kind != PROGNOSIS_OUTPUT_KIND or self.output_label != PROGNOSIS_OUTPUT_LABEL or self.interpretation != PROGNOSIS_INTERPRETATION:
            raise ValueError("prognosis output contract is frozen")
        if isinstance(self.value, bool) or not isinstance(self.value, (int, float)) or not math.isfinite(self.value):
            raise ValueError("value must be finite")
        if self.survival_estimates is not None and not isinstance(self.survival_estimates, SurvivalProbabilityEstimates):
            raise TypeError("survival_estimates must be SurvivalProbabilityEstimates or None")


@dataclass(frozen=True, slots=True)
class SubtypeClassificationResult(SerializableContract):
    lineage: ResultLineage
    predicted_class: str
    class_order: tuple[str, ...]
    probabilities: tuple[float, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.lineage, ResultLineage):
            raise TypeError("lineage must be ResultLineage")
        if self.class_order != FROZEN_SUBTYPE_CLASS_ORDER:
            raise ValueError("class_order must equal frozen subtype class order")
        if self.predicted_class not in FROZEN_SUBTYPE_CLASS_ORDER:
            raise ValueError("predicted_class must be a frozen subtype class")
        if len(self.probabilities) != 6 or any(isinstance(p, bool) or not isinstance(p, (int, float)) or not math.isfinite(p) for p in self.probabilities):
            raise ValueError("probabilities must be six finite values")
        if not math.isclose(sum(self.probabilities), 1.0, abs_tol=1e-8, rel_tol=0):
            raise ValueError("probabilities must sum to one")


@dataclass(frozen=True, slots=True)
class TrackError(SerializableContract):
    code: str
    message: str
    track: AnalysisTrack
    missing_fields: tuple[str, ...] = ()
    invalid_fields: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _text(self.code, "code"); _text(self.message, "message")
        if not isinstance(self.track, AnalysisTrack):
            raise TypeError("track must be AnalysisTrack")
        _field_names(self.missing_fields, "missing_fields"); _field_names(self.invalid_fields, "invalid_fields")


@dataclass(frozen=True, slots=True)
class RequestError(SerializableContract):
    code: str
    message: str
    fields: tuple[str, ...] = ()
    def __post_init__(self) -> None:
        _text(self.code, "code"); _text(self.message, "message"); _field_names(self.fields, "fields")


@dataclass(frozen=True, slots=True)
class TrackOutcome(SerializableContract):
    track: AnalysisTrack
    state: TrackReadinessState
    result: PrognosisResult | SubtypeClassificationResult | None
    error: TrackError | None
    def __post_init__(self) -> None:
        if not isinstance(self.track, AnalysisTrack) or not isinstance(self.state, TrackReadinessState):
            raise TypeError("track/state must be R9 enums")
        ready = self.state is TrackReadinessState.READY
        if ready and (self.result is None or self.error is not None):
            raise ValueError("READY outcome requires a result and no error")
        if not ready and (self.result is not None or self.error is None):
            raise ValueError("non-ready outcome requires an error and no result")


@dataclass(frozen=True, slots=True)
class AnalysisResponse(SerializableContract):
    schema_version: str
    requested_tracks: tuple[AnalysisTrack, ...]
    outcomes: tuple[TrackOutcome, ...]
    request_errors: tuple[RequestError, ...]
    def __post_init__(self) -> None:
        _text(self.schema_version, "schema_version")
        if not all(isinstance(v, AnalysisTrack) for v in self.requested_tracks) or not all(isinstance(v, TrackOutcome) for v in self.outcomes) or not all(isinstance(v, RequestError) for v in self.request_errors):
            raise TypeError("AnalysisResponse contains invalid contract values")


@dataclass(frozen=True, slots=True)
class PrognosticFeatureEffectView(SerializableContract):
    effect: PrognosticFeatureEffect
    def __post_init__(self) -> None:
        if not isinstance(self.effect, PrognosticFeatureEffect):
            raise TypeError("effect must be PrognosticFeatureEffect")


@dataclass(frozen=True, slots=True)
class PrognosticFeatureAnalysisView(SerializableContract):
    analysis_id: str
    schema_version: str
    source_r6_experiment_id: str
    coef_eps: float
    effects: tuple[PrognosticFeatureEffectView, ...]
    interpretation: str
    def __post_init__(self) -> None:
        for name in ("analysis_id", "schema_version", "source_r6_experiment_id", "interpretation"):
            _text(getattr(self, name), name)
        if not isinstance(self.coef_eps, (int, float)) or not math.isfinite(self.coef_eps) or len(self.effects) != 68:
            raise ValueError("aggregate view must have finite coefficient threshold and 68 effects")


@dataclass(frozen=True, slots=True)
class AggregateAnalysisError(SerializableContract):
    code: str
    message: str
    def __post_init__(self) -> None:
        _text(self.code, "code"); _text(self.message, "message")


@dataclass(frozen=True, slots=True)
class PrognosticFeatureAnalysisOutcome(SerializableContract):
    view: PrognosticFeatureAnalysisView | None
    error: AggregateAnalysisError | None
    def __post_init__(self) -> None:
        if (self.view is None) == (self.error is None):
            raise ValueError("exactly one of view or error is required")
