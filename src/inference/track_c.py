"""Exact persisted-pipeline inference for frozen R7 Track C."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from src.artifacts.inference_registry import ArtifactEntry
from src.contracts.inference import (
    AnalysisTrack,
    FROZEN_SUBTYPE_CLASS_ORDER,
    ResultLineage,
    SubtypeClassificationResult,
)
from src.evaluation.classification import reorder_and_validate_probabilities

from ._common import InferenceAdapterError, ordered_frame


class TrackCInferenceAdapter:
    """Runs the persisted R7 pipeline; it never fits or externally transforms input."""

    def __init__(self, entry: ArtifactEntry) -> None:
        if entry.track is not AnalysisTrack.TRACK_C or not entry.available or entry.model is None:
            raise InferenceAdapterError("R7 canonical artifact is unavailable")
        self.required_fields = entry.required_fields
        self._pipeline = entry.model
        self._lineage = ResultLineage(AnalysisTrack.TRACK_C, str(entry.metadata["experiment_id"]), "r7-v1", entry.contract_sha256)

    def predict(self, features: Mapping[str, object]) -> SubtypeClassificationResult:
        frame = ordered_frame(features, self.required_fields)
        predicted_values = np.asarray(self._pipeline.predict(frame), dtype=object).reshape(-1)
        if predicted_values.size != 1:
            raise InferenceAdapterError("R7 pipeline emitted an invalid prediction")
        predicted = str(predicted_values[0])
        if predicted not in FROZEN_SUBTYPE_CLASS_ORDER:
            raise InferenceAdapterError("R7 pipeline emitted an unsupported subtype")
        output = reorder_and_validate_probabilities(
            self._pipeline.predict_proba(frame), self._pipeline.classes_, FROZEN_SUBTYPE_CLASS_ORDER
        )
        return SubtypeClassificationResult(
            self._lineage, predicted, FROZEN_SUBTYPE_CLASS_ORDER,
            tuple(float(value) for value in output.probabilities[0]),
        )
