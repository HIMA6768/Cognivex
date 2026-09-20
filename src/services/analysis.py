"""Framework-independent orchestration over verified frozen model artifacts."""

from __future__ import annotations

from collections.abc import Mapping
from numbers import Real
from pathlib import Path

from src.artifacts.inference_registry import CanonicalArtifactRegistry, build_canonical_registry
from src.contracts.inference import (
    AnalysisRequest, AnalysisResponse, AnalysisTrack, R9_SCHEMA_VERSION,
    RequestError, TrackError, TrackOutcome, TrackReadinessState,
)
from src.inference._common import InferenceAdapterError
from src.inference.track_a import TrackAInferenceAdapter
from src.inference.track_b import TrackBInferenceAdapter
from src.inference.track_c import TrackCInferenceAdapter
from src.contracts.inference import AggregateAnalysisError, PrognosticFeatureAnalysisOutcome
from src.contracts.model_evaluation import ModelEvaluationOutcome
from .prognostic_features import read_prognostic_feature_analysis
from .model_evaluation import get_frozen_model_evaluation


class AnalysisService:
    """One-time artifact initialization and request-local, non-persisting analysis."""

    def __init__(self, registry: CanonicalArtifactRegistry) -> None:
        self.registry = registry
        self.allowed_input_fields = registry.global_contract.raw_fields
        self._adapters: dict[AnalysisTrack, object] = {}
        factories = {
            AnalysisTrack.TRACK_A: TrackAInferenceAdapter,
            AnalysisTrack.TRACK_B: TrackBInferenceAdapter,
            AnalysisTrack.TRACK_C: TrackCInferenceAdapter,
        }
        for track, factory in factories.items():
            entry = registry.entry(track)
            if entry.available:
                try:
                    self._adapters[track] = factory(entry)
                except Exception:
                    # The registry remains immutable; the track becomes safely unavailable.
                    pass
        self.adapter_call_counts = {track: 0 for track in AnalysisTrack}

    @classmethod
    def from_canonical_artifacts(cls, repository_root: Path) -> "AnalysisService":
        return cls(build_canonical_registry(repository_root))

    def _resolve_tracks(self, request: AnalysisRequest) -> tuple[AnalysisTrack, ...] | RequestError:
        if request.requested_tracks is None:
            return tuple(AnalysisTrack)
        if not request.requested_tracks:
            return RequestError("INVALID_REQUESTED_TRACKS", "At least one requested track is required")
        if len(set(request.requested_tracks)) != len(request.requested_tracks):
            return RequestError("DUPLICATE_REQUESTED_TRACK", "Requested tracks must be unique")
        if not all(isinstance(track, AnalysisTrack) for track in request.requested_tracks):
            return RequestError("INVALID_REQUESTED_TRACK", "Requested tracks are invalid")
        return request.requested_tracks

    def _global_errors(self, request: AnalysisRequest) -> tuple[RequestError, ...]:
        unknown = tuple(sorted(set(request.features) - set(self.allowed_input_fields)))
        if unknown:
            return (RequestError("UNKNOWN_FIELD", "Request contains unsupported field names", unknown),)
        invalid = tuple(sorted(
            name for name, value in request.features.items()
            if isinstance(value, (bool, list, tuple, set, dict)) or not isinstance(value, (str, Real, type(None)))
        ))
        if invalid:
            return (RequestError("INVALID_FIELD_VALUE", "Request contains unsupported field value types", invalid),)
        return ()

    @staticmethod
    def _error(track: AnalysisTrack, state: TrackReadinessState, code: str, message: str, *, missing: tuple[str, ...] = ()) -> TrackOutcome:
        return TrackOutcome(track, state, None, TrackError(code, message, track, missing_fields=missing))

    def _evaluate_track(self, track: AnalysisTrack, features: Mapping[str, object]) -> TrackOutcome:
        entry = self.registry.entry(track)
        if not entry.available or track not in self._adapters:
            return self._error(track, TrackReadinessState.ARTIFACT_UNAVAILABLE, "ARTIFACT_UNAVAILABLE", "Canonical artifact is unavailable")
        missing = tuple(field for field in entry.required_fields if field not in features)
        if missing:
            return self._error(track, TrackReadinessState.MISSING_REQUIRED_FIELDS, "MISSING_REQUIRED_FIELDS", "Required input fields are missing", missing=missing)
        try:
            self.adapter_call_counts[track] += 1
            result = self._adapters[track].predict(features)  # type: ignore[attr-defined]
            return TrackOutcome(track, TrackReadinessState.READY, result, None)
        except InferenceAdapterError:
            return self._error(track, TrackReadinessState.INVALID_INPUT, "INVALID_INPUT", "Input is incompatible with the frozen model contract")
        except Exception:
            return self._error(track, TrackReadinessState.INFERENCE_ERROR, "INFERENCE_ERROR", "Inference could not be completed")

    def analyze(self, request: AnalysisRequest) -> AnalysisResponse:
        errors = list(self._global_errors(request))
        tracks = self._resolve_tracks(request)
        if isinstance(tracks, RequestError):
            return AnalysisResponse(R9_SCHEMA_VERSION, (), (), tuple([*errors, tracks]))
        if errors:
            return AnalysisResponse(R9_SCHEMA_VERSION, tracks, (), tuple(errors))
        return AnalysisResponse(R9_SCHEMA_VERSION, tracks, tuple(self._evaluate_track(track, request.features) for track in tracks), ())

    def get_prognostic_feature_analysis(self) -> PrognosticFeatureAnalysisOutcome:
        if not self.registry.r8.available:
            return PrognosticFeatureAnalysisOutcome(
                None, AggregateAnalysisError("ARTIFACT_UNAVAILABLE", "Aggregate analysis artifact is unavailable")
            )
        try:
            return PrognosticFeatureAnalysisOutcome(read_prognostic_feature_analysis(self.registry.r8), None)
        except Exception:
            return PrognosticFeatureAnalysisOutcome(
                None, AggregateAnalysisError("ARTIFACT_UNAVAILABLE", "Aggregate analysis artifact is unavailable")
            )

    def get_model_evaluation(self) -> ModelEvaluationOutcome:
        """Return checksum-verified aggregate metrics without exposing runtime artifacts."""
        return get_frozen_model_evaluation(self.registry.repository_root)
