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
)


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


def prognosis(lineage: ResultLineage, score: float) -> PrognosisResult:
    return PrognosisResult(lineage, PROGNOSIS_OUTPUT_KIND, PROGNOSIS_OUTPUT_LABEL, score, PROGNOSIS_INTERPRETATION)
