"""R5 lifelines adapter tests."""

from __future__ import annotations

import warnings

import numpy as np
import pytest
from lifelines.exceptions import ConvergenceWarning

from src.contracts import PHDiagnosticStatus
from src.modeling.survival import CoxFitError, LifelinesCoxPHAdapter


def _fixture() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    generator = np.random.default_rng(20260918)
    first = generator.normal(size=120)
    second = generator.normal(size=120)
    durations = generator.exponential(scale=np.exp(-0.25 * first + 0.15 * second) * 30.0) + 0.1
    events = generator.binomial(1, 0.7, size=120).astype(int)
    return np.column_stack([first, second]), durations, events


def test_adapter_uses_exact_approved_configuration_and_separate_targets() -> None:
    values, durations, events = _fixture()
    adapter = LifelinesCoxPHAdapter()

    adapter.fit(values, durations, events, ("age", "tumor_size"))

    assert adapter.fitter.baseline_estimation_method == "breslow"
    assert adapter.fitter.penalizer == 0.0
    assert adapter.fitter.l1_ratio == 0.0
    assert adapter.fitter.strata is None
    assert adapter.fitter.alpha == 0.05
    assert adapter.feature_names == ("age", "tumor_size")
    assert "__duration" not in adapter.feature_names
    assert "__event" not in adapter.feature_names


def test_adapter_returns_ordered_risk_and_coefficient_evidence() -> None:
    values, durations, events = _fixture()
    adapter = LifelinesCoxPHAdapter()
    adapter.fit(values, durations, events, ("age", "tumor_size"))

    risks = adapter.predict_risk(values[:4])
    coefficients = adapter.coefficient_estimates()

    assert risks.shape == (4,)
    assert np.isfinite(risks).all()
    assert tuple(item.feature_name for item in coefficients) == ("age", "tumor_size")
    assert all(item.hazard_ratio == pytest.approx(np.exp(item.coefficient)) for item in coefficients)
    assert all(0 <= item.p_value <= 1 for item in coefficients)


def test_ph_diagnostics_are_machine_readable_and_rank_transformed() -> None:
    values, durations, events = _fixture()
    adapter = LifelinesCoxPHAdapter()
    adapter.fit(values, durations, events, ("age", "tumor_size"))

    diagnostics = adapter.evaluate_ph_assumptions()

    assert diagnostics.status in {PHDiagnosticStatus.PASSED, PHDiagnosticStatus.FLAGGED}
    assert diagnostics.time_transform == "rank"
    assert diagnostics.threshold == 0.05
    assert tuple(item.feature_name for item in diagnostics.features) == ("age", "tumor_size")


def test_material_convergence_warning_stops_fit(monkeypatch: pytest.MonkeyPatch) -> None:
    values, durations, events = _fixture()
    adapter = LifelinesCoxPHAdapter()

    def warn_only(*args, **kwargs):
        warnings.warn("singular design", ConvergenceWarning)
        return adapter.fitter

    monkeypatch.setattr(adapter.fitter, "fit", warn_only)

    with pytest.raises(CoxFitError, match="material convergence warning") as exc_info:
        adapter.fit(values, durations, events, ("age", "tumor_size"))

    assert exc_info.value.warnings == ("singular design",)


def test_diagnostic_failure_is_returned_not_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    values, durations, events = _fixture()
    adapter = LifelinesCoxPHAdapter()
    adapter.fit(values, durations, events, ("age", "tumor_size"))

    def fail(*args, **kwargs):
        raise ValueError("residual calculation failed")

    monkeypatch.setattr("src.modeling.survival.proportional_hazard_test", fail)

    diagnostics = adapter.evaluate_ph_assumptions()

    assert diagnostics.status is PHDiagnosticStatus.FAILED
    assert diagnostics.error_message == "residual calculation failed"
