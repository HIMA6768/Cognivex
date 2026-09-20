"""Small shared, non-persisting inference helpers."""

from __future__ import annotations

import math
from collections.abc import Mapping

import numpy as np
import pandas as pd

from src.contracts.inference import (
    PROGNOSIS_INTERPRETATION,
    PROGNOSIS_OUTPUT_KIND,
    PROGNOSIS_OUTPUT_LABEL,
    PrognosisResult,
    ResultLineage,
    SurvivalProbabilityEstimates,
)


SURVIVAL_HORIZONS_MONTHS = (12.0, 36.0, 60.0)


class InferenceAdapterError(RuntimeError):
    """A safe adapter failure that callers map to a code-only error."""


def ordered_frame(
    features: Mapping[str, object], fields: tuple[str, ...], *, categorical_fields: tuple[str, ...] = ()
) -> pd.DataFrame:
    """Build one ordered row without logging or retaining source values."""
    missing = tuple(name for name in fields if name not in features)
    if missing:
        raise InferenceAdapterError("required input fields are missing")
    values = {name: features[name] for name in fields}
    for name in categorical_fields:
        value = values[name]
        if value is not None and not pd.isna(value):
            values[name] = str(value)
    return pd.DataFrame([values], columns=list(fields))


def finite_scalar(values: object, track_name: str) -> float:
    array = np.asarray(values, dtype=float).reshape(-1)
    if array.size != 1 or not math.isfinite(float(array[0])):
        raise InferenceAdapterError(f"{track_name} produced a non-finite score")
    return float(array[0])


def cox_survival_estimates(
    fitter: object,
    transformed_values: object,
    feature_names: tuple[str, ...],
    track_name: str,
) -> SurvivalProbabilityEstimates:
    """Evaluate the fitted Cox survival function at fixed in-range month horizons."""
    baseline = getattr(fitter, "baseline_cumulative_hazard_", None)
    if baseline is None or not hasattr(baseline, "index"):
        raise InferenceAdapterError(f"{track_name} baseline survival is unavailable")
    try:
        index = np.asarray(baseline.index, dtype=float)
    except (TypeError, ValueError) as error:
        raise InferenceAdapterError(f"{track_name} baseline survival is unavailable") from error
    if index.size == 0 or not np.isfinite(index).all() or min(SURVIVAL_HORIZONS_MONTHS) < float(index.min()) or max(SURVIVAL_HORIZONS_MONTHS) > float(index.max()):
        raise InferenceAdapterError(f"{track_name} baseline horizon does not cover required survival estimates")

    matrix = np.asarray(transformed_values, dtype=float)
    if matrix.ndim != 2 or matrix.shape != (1, len(feature_names)):
        raise InferenceAdapterError(f"{track_name} transformed feature matrix is invalid")
    try:
        predicted = fitter.predict_survival_function(  # type: ignore[attr-defined]
            pd.DataFrame(matrix, columns=list(feature_names)),
            times=np.asarray(SURVIVAL_HORIZONS_MONTHS, dtype=float),
        )
        values = tuple(float(predicted.loc[horizon].iloc[0]) for horizon in SURVIVAL_HORIZONS_MONTHS)
    except Exception as error:
        raise InferenceAdapterError(f"{track_name} survival estimation failed") from error
    return SurvivalProbabilityEstimates(*values)


def prognosis(
    lineage: ResultLineage,
    score: float,
    survival_estimates: SurvivalProbabilityEstimates | None = None,
) -> PrognosisResult:
    return PrognosisResult(
        lineage,
        PROGNOSIS_OUTPUT_KIND,
        PROGNOSIS_OUTPUT_LABEL,
        score,
        PROGNOSIS_INTERPRETATION,
        survival_estimates,
    )
