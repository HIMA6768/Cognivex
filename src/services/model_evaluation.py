"""Safe service-level facade for aggregate frozen evaluation metrics."""

from __future__ import annotations

import logging
from pathlib import Path

from src.artifacts.model_evaluation import (
    model_evaluation_artifact_file_state,
    read_frozen_model_evaluation,
)
from src.contracts.model_evaluation import ModelEvaluationError, ModelEvaluationOutcome


LOGGER = logging.getLogger(__name__)


def get_frozen_model_evaluation(repository_root: Path) -> ModelEvaluationOutcome:
    """Return read-only aggregate metrics or a caller-safe unavailable state."""
    try:
        return ModelEvaluationOutcome(read_frozen_model_evaluation(repository_root), None)
    except Exception as error:
        LOGGER.exception(
            "[ONCOMAP_MODEL_EVAL_ERROR] exception_class=%s exception_message=%s "
            "repository_root=%s aggregate_artifacts=%s",
            type(error).__name__,
            str(error),
            Path(repository_root).resolve(),
            model_evaluation_artifact_file_state(repository_root),
        )
        return ModelEvaluationOutcome(
            None,
            ModelEvaluationError(
                "ARTIFACT_UNAVAILABLE",
                "Frozen aggregate model evaluation metrics are unavailable.",
            ),
        )
