"""Lifelines-backed R5 Cox PH adapter with explicit failure evidence."""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from lifelines import CoxPHFitter
from lifelines.exceptions import ConvergenceWarning
from lifelines.statistics import proportional_hazard_test

from src.contracts import (
    CoefficientEstimate,
    PHDiagnosticStatus,
    PHDiagnostics,
    PHFeatureDiagnostic,
)


class CoxFitError(RuntimeError):
    """A stopped baseline fit carrying convergence evidence without a fallback."""

    def __init__(self, message: str, *, warnings: tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.warnings = warnings


class LifelinesCoxPHAdapter:
    """Approved unpenalized CoxPHFitter boundary for transformed Track A data."""

    _DURATION = "__duration"
    _EVENT = "__event"

    def __init__(self) -> None:
        self.fitter = CoxPHFitter(
            baseline_estimation_method="breslow",
            penalizer=0.0,
            l1_ratio=0.0,
            strata=None,
            alpha=0.05,
        )
        self.feature_names: tuple[str, ...] = ()
        self._training_frame: pd.DataFrame | None = None
        self.convergence_warnings: tuple[str, ...] = ()

    def fit(self, values, durations, events, feature_names: tuple[str, ...]) -> None:
        matrix = np.asarray(values, dtype=float)
        duration_values = np.asarray(durations, dtype=float)
        event_values = np.asarray(events, dtype=int)
        if matrix.ndim != 2 or matrix.shape[1] != len(feature_names):
            raise ValueError("transformed values must align with feature_names")
        if matrix.shape[0] != len(duration_values) or len(duration_values) != len(event_values):
            raise ValueError("predictors, durations, and events must be row-aligned")
        if self._DURATION in feature_names or self._EVENT in feature_names:
            raise ValueError("reserved target names cannot be predictors")
        frame = pd.DataFrame(matrix, columns=list(feature_names))
        frame[self._DURATION] = duration_values
        frame[self._EVENT] = event_values
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ConvergenceWarning)
            try:
                self.fitter.fit(frame, duration_col=self._DURATION, event_col=self._EVENT)
            except Exception as error:
                convergence = tuple(str(item.message) for item in caught if issubclass(item.category, ConvergenceWarning))
                raise CoxFitError(f"Cox PH fitting failed: {error}", warnings=convergence) from error
        convergence = tuple(str(item.message) for item in caught if issubclass(item.category, ConvergenceWarning))
        if convergence:
            raise CoxFitError("Cox PH fitting produced a material convergence warning", warnings=convergence)
        self.feature_names = feature_names
        self._training_frame = frame
        self.convergence_warnings = ()

    def _require_fitted(self) -> None:
        if self._training_frame is None:
            raise RuntimeError("Cox PH adapter has not been fitted")

    def predict_risk(self, values) -> np.ndarray:
        self._require_fitted()
        matrix = np.asarray(values, dtype=float)
        if matrix.ndim != 2 or matrix.shape[1] != len(self.feature_names):
            raise ValueError("prediction matrix does not match fitted feature order")
        frame = pd.DataFrame(matrix, columns=list(self.feature_names))
        return self.fitter.predict_log_partial_hazard(frame).to_numpy(dtype=float)

    def coefficient_estimates(self) -> tuple[CoefficientEstimate, ...]:
        self._require_fitted()
        summary = self.fitter.summary
        return tuple(
            CoefficientEstimate(
                feature_name=name,
                coefficient=float(summary.loc[name, "coef"]),
                hazard_ratio=float(summary.loc[name, "exp(coef)"]),
                standard_error=float(summary.loc[name, "se(coef)"]),
                coefficient_ci_lower_95=float(summary.loc[name, "coef lower 95%"]),
                coefficient_ci_upper_95=float(summary.loc[name, "coef upper 95%"]),
                hazard_ratio_ci_lower_95=float(summary.loc[name, "exp(coef) lower 95%"]),
                hazard_ratio_ci_upper_95=float(summary.loc[name, "exp(coef) upper 95%"]),
                z_statistic=float(summary.loc[name, "z"]),
                p_value=float(summary.loc[name, "p"]),
            )
            for name in self.feature_names
        )

    def evaluate_ph_assumptions(self, *, threshold: float = 0.05) -> PHDiagnostics:
        self._require_fitted()
        assert self._training_frame is not None
        try:
            result = proportional_hazard_test(
                self.fitter,
                self._training_frame,
                time_transform="rank",
            )
            summary = result.summary
            features = tuple(
                PHFeatureDiagnostic(
                    feature_name=name,
                    test_statistic=float(summary.loc[name, "test_statistic"]),
                    p_value=float(summary.loc[name, "p"]),
                    flagged=float(summary.loc[name, "p"]) < threshold,
                )
                for name in self.feature_names
            )
        except Exception as error:
            return PHDiagnostics(
                status=PHDiagnosticStatus.FAILED,
                time_transform="rank",
                threshold=threshold,
                features=(),
                error_message=str(error),
            )
        status = (
            PHDiagnosticStatus.FLAGGED
            if any(feature.flagged for feature in features)
            else PHDiagnosticStatus.PASSED
        )
        return PHDiagnostics(status, "rank", threshold, features, None)
