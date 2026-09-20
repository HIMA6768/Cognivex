"""Exact transform-only inference for frozen R5 Track A."""

from __future__ import annotations

from collections.abc import Mapping

from src.artifacts.inference_registry import ArtifactEntry
from src.contracts.inference import AnalysisTrack, ResultLineage, PrognosisResult
from src.preprocessing.pipelines import get_transformed_feature_names

from ._common import InferenceAdapterError, finite_scalar, ordered_frame, prognosis


class TrackAInferenceAdapter:
    """Uses only persisted R5 preprocessing and Cox adapter state."""

    def __init__(self, entry: ArtifactEntry) -> None:
        if entry.track is not AnalysisTrack.TRACK_A or not entry.available or entry.preprocessor is None or entry.model is None:
            raise InferenceAdapterError("R5 canonical artifact is unavailable")
        self.required_fields = entry.required_fields
        self._preprocessor = entry.preprocessor
        self._model = entry.model
        self._model_feature_names = tuple(getattr(self._model, "feature_names", ()))
        self._lineage = ResultLineage(AnalysisTrack.TRACK_A, str(entry.metadata["experiment_id"]), "r5-v1", entry.contract_sha256)

    def predict(self, features: Mapping[str, object]) -> PrognosisResult:
        matrix = self._preprocessor.transform(
            ordered_frame(
                features, self.required_fields,
                categorical_fields=("tumor_stage", "er_status_measured_by_ihc", "pr_status", "her2_status"),
            )
        )
        if tuple(get_transformed_feature_names(self._preprocessor)) != self._model_feature_names:
            raise InferenceAdapterError("R5 transformed feature order verification failed")
        return prognosis(self._lineage, finite_scalar(self._model.predict_risk(matrix), "R5"))
