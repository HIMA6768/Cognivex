"""Safe service-level facade for aggregate frozen evaluation metrics."""

from __future__ import annotations

from pathlib import Path

from src.artifacts.model_evaluation import read_frozen_model_evaluation
from src.contracts.model_evaluation import ModelEvaluationError, ModelEvaluationOutcome


def get_frozen_model_evaluation(repository_root: Path) -> ModelEvaluationOutcome:
    """Return read-only aggregate metrics or a caller-safe unavailable state."""
    try:
        return ModelEvaluationOutcome(read_frozen_model_evaluation(repository_root), None)
    except Exception:
        return ModelEvaluationOutcome(
            None,
            ModelEvaluationError(
                "ARTIFACT_UNAVAILABLE",
                "Frozen aggregate model evaluation metrics are unavailable.",
            ),
        )
