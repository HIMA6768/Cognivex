"""Configurable lifelines adapter for R6 penalized Cox candidates."""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from lifelines import CoxPHFitter
from lifelines.exceptions import ConvergenceWarning

from src.contracts import TrackBHyperparameters
from src.modeling.survival import CoxFitError


class PenalizedCoxPHAdapter:
    """Fit one predefined penalized Cox configuration on a fixed feature order."""

    _DURATION = "__duration"
    _EVENT = "__event"

    def __init__(self, configuration: TrackBHyperparameters) -> None:
        if not isinstance(configuration, TrackBHyperparameters):
            raise TypeError("configuration must be TrackBHyperparameters")
        self.configuration = configuration
        self.fitter = CoxPHFitter(
            baseline_estimation_method="breslow",
            penalizer=float(configuration.penalizer),
            l1_ratio=float(configuration.l1_ratio),
            strata=None,
            alpha=0.05,
        )
        self.feature_names: tuple[str, ...] = ()
        self.convergence_warnings: tuple[str, ...] = ()
        self._fitted = False

    def fit(self, values, durations, events, feature_names: tuple[str, ...]) -> None:
        matrix = np.asarray(values, dtype=float)
        duration_values = np.asarray(durations, dtype=float)
        event_values = np.asarray(events, dtype=int)
        if matrix.ndim != 2 or matrix.shape[1] != len(feature_names):
            raise ValueError("transformed values must align with feature_names")
        if matrix.shape[0] != len(duration_values) or len(duration_values) != len(event_values):
            raise ValueError("predictors, durations, and events must be row-aligned")
        if not np.isfinite(matrix).all() or not np.isfinite(duration_values).all():
            raise ValueError("Cox inputs must be finite")
        if not set(np.unique(event_values)).issubset({0, 1}):
            raise ValueError("event values must use canonical 0/1 coding")
        frame = pd.DataFrame(matrix, columns=list(feature_names))
        frame[self._DURATION] = duration_values
        frame[self._EVENT] = event_values
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ConvergenceWarning)
            try:
                self.fitter.fit(frame, duration_col=self._DURATION, event_col=self._EVENT)
            except Exception as error:
                convergence = tuple(
                    str(item.message)
                    for item in caught
                    if issubclass(item.category, ConvergenceWarning)
                )
                raise CoxFitError(
                    f"penalized Cox fitting failed: {error}", warnings=convergence
                ) from error
        convergence = tuple(
            str(item.message)
            for item in caught
            if issubclass(item.category, ConvergenceWarning)
        )
        if convergence:
            raise CoxFitError(
                "penalized Cox fitting produced a material convergence warning",
                warnings=convergence,
            )
        self.feature_names = feature_names
        self.convergence_warnings = ()
        self._fitted = True

    def predict_risk(self, values) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("penalized Cox adapter has not been fitted")
        matrix = np.asarray(values, dtype=float)
        if matrix.ndim != 2 or matrix.shape[1] != len(self.feature_names):
            raise ValueError("prediction matrix does not match fitted feature order")
        frame = pd.DataFrame(matrix, columns=list(self.feature_names))
        return self.fitter.predict_log_partial_hazard(frame).to_numpy(dtype=float)

