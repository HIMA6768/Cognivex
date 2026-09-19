"""Censoring-aware evaluation helpers."""

from .survival import diagnose_design_matrix, harrell_c_index
from .classification import (
    ProbabilityOutput,
    evaluate_classification,
    prediction_digest,
    probability_digest,
    reorder_and_validate_probabilities,
)

__all__ = [
    "ProbabilityOutput",
    "diagnose_design_matrix",
    "evaluate_classification",
    "harrell_c_index",
    "prediction_digest",
    "probability_digest",
    "reorder_and_validate_probabilities",
]
