"""Exact transform-only inference for frozen R6 Track B."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from src.artifacts.inference_registry import ArtifactEntry
from src.contracts.inference import AnalysisTrack, PrognosisResult, ResultLineage
from src.preprocessing.track_b import track_b_feature_names

from ._common import cox_survival_estimates, InferenceAdapterError, finite_scalar, ordered_frame, prognosis

_CLINICAL_CATEGORICAL = ("tumor_stage", "er_status_measured_by_ihc", "pr_status", "her2_status")


class TrackBInferenceAdapter:
    """Uses the persisted R6 clinical/genomic preprocessing pipeline exactly once."""

    def __init__(self, entry: ArtifactEntry) -> None:
        if entry.track is not AnalysisTrack.TRACK_B or not entry.available or entry.preprocessor is None or entry.model is None:
            raise InferenceAdapterError("R6 canonical artifact is unavailable")
        self.required_fields = entry.required_fields
        self._preprocessor = entry.preprocessor
        self._model = entry.model
        self.model_feature_names = tuple(getattr(self._model, "feature_names", ()))
        self._lineage = ResultLineage(AnalysisTrack.TRACK_B, str(entry.metadata["experiment_id"]), "r6-v1", entry.contract_sha256)

    def predict(self, features: Mapping[str, object]) -> PrognosisResult:
        frame = ordered_frame(features, self.required_fields, categorical_fields=_CLINICAL_CATEGORICAL)
        matrix = np.asarray(self._preprocessor.transform(frame), dtype=float)
        if tuple(track_b_feature_names(self._preprocessor)) != self.model_feature_names:
            raise InferenceAdapterError("R6 transformed feature order verification failed")
        return prognosis(
            self._lineage,
            finite_scalar(self._model.predict_risk(matrix), "R6"),
            cox_survival_estimates(self._model.fitter, matrix, self.model_feature_names, "R6"),
        )
