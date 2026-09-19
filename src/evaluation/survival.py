"""Deterministic R5 concordance and design-matrix diagnostics."""

from __future__ import annotations

import numpy as np
from lifelines.utils import concordance_index

from src.contracts import ConcordanceResult, MatrixDiagnostic


def harrell_c_index(
    durations,
    events,
    risk_scores,
    *,
    split: str,
    cohort_fingerprint: str,
) -> ConcordanceResult:
    """Evaluate higher-is-higher-hazard log-risk without direction inversion."""
    durations_array = np.asarray(durations, dtype=float)
    events_array = np.asarray(events, dtype=int)
    risks_array = np.asarray(risk_scores, dtype=float)
    if not (durations_array.ndim == events_array.ndim == risks_array.ndim == 1):
        raise ValueError("durations, events, and risk_scores must be one-dimensional")
    if not (len(durations_array) == len(events_array) == len(risks_array)) or not len(durations_array):
        raise ValueError("durations, events, and risk_scores must be non-empty and aligned")
    if not np.isfinite(durations_array).all() or not np.isfinite(risks_array).all():
        raise ValueError("durations and risk_scores must be finite")
    if not np.isin(events_array, (0, 1)).all():
        raise ValueError("events must use 1=event and 0=censored")
    score = float(concordance_index(durations_array, -risks_array, events_array))
    event_count = int(events_array.sum())
    return ConcordanceResult(
        metric_name="harrell_c_index",
        split=split,
        row_count=len(events_array),
        event_count=event_count,
        censored_count=len(events_array) - event_count,
        c_index=score,
        prediction_quantity="log_partial_hazard",
        score_direction="higher_risk_is_higher_hazard",
        risk_negated_for_metric=True,
        cohort_fingerprint=cohort_fingerprint,
    )


def diagnose_design_matrix(values, feature_names: tuple[str, ...]) -> MatrixDiagnostic:
    """Return deterministic pre-fit rank, duplicate, variance, and dependency evidence."""
    matrix = np.asarray(values, dtype=float)
    if matrix.ndim != 2 or matrix.shape[1] != len(feature_names):
        raise ValueError("matrix columns must align with feature_names")
    all_finite = bool(np.isfinite(matrix).all())
    safe_matrix = np.nan_to_num(matrix, nan=0.0, posinf=0.0, neginf=0.0)
    rank = int(np.linalg.matrix_rank(safe_matrix))
    condition_number = float(np.linalg.cond(safe_matrix))
    zero_variance = tuple(
        feature_names[index]
        for index in range(matrix.shape[1])
        if np.ptp(safe_matrix[:, index]) == 0
    )
    duplicate_pairs = tuple(
        (feature_names[left], feature_names[right])
        for left in range(matrix.shape[1])
        for right in range(left + 1, matrix.shape[1])
        if np.array_equal(safe_matrix[:, left], safe_matrix[:, right])
    )
    dependencies: list[str] = []
    if rank < matrix.shape[1]:
        _, _, vectors = np.linalg.svd(safe_matrix, full_matrices=True)
        for vector in vectors[rank:]:
            if vector[np.argmax(np.abs(vector))] < 0:
                vector = -vector
            terms = [
                f"{coefficient:.12g}*{feature_names[index]}"
                for index, coefficient in enumerate(vector)
                if abs(float(coefficient)) > 1e-10
            ]
            dependencies.append(" + ".join(terms) + " = 0")
    return MatrixDiagnostic(
        row_count=matrix.shape[0],
        feature_count=matrix.shape[1],
        rank=rank,
        condition_number=condition_number,
        zero_variance_features=zero_variance,
        duplicate_column_pairs=duplicate_pairs,
        linear_dependencies=tuple(dependencies),
        all_finite=all_finite,
    )
