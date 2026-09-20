from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.artifacts.inference_registry import build_canonical_registry
from src.contracts.inference import AnalysisTrack
from src.inference._common import InferenceAdapterError, cox_survival_estimates


ROOT = Path(__file__).resolve().parents[1]
HORIZONS = (12.0, 36.0, 60.0)


@pytest.mark.parametrize("track", (AnalysisTrack.TRACK_A, AnalysisTrack.TRACK_B))
def test_frozen_cox_estimates_match_public_lifelines_off_index_interpolation(track: AnalysisTrack) -> None:
    model = build_canonical_registry(ROOT).entry(track).model
    assert model is not None
    fitter = model.fitter
    synthetic_values = np.zeros((1, len(model.feature_names)))
    expected = fitter.predict_survival_function(
        pd.DataFrame(synthetic_values, columns=model.feature_names),
        times=HORIZONS,
    ).iloc[:, 0].to_numpy(dtype=float)

    estimates = cox_survival_estimates(fitter, synthetic_values, model.feature_names, track.value)

    assert all(horizon not in fitter.baseline_cumulative_hazard_.index for horizon in HORIZONS)
    assert np.allclose(
        (
            estimates.survival_probability_1y,
            estimates.survival_probability_3y,
            estimates.survival_probability_5y,
        ),
        expected,
        rtol=0,
        atol=1e-12,
    )


def test_cox_estimates_reject_horizon_outside_fitted_baseline() -> None:
    class ShortBaselineFitter:
        baseline_cumulative_hazard_ = pd.DataFrame({"baseline": [0.0, 0.1]}, index=[0.0, 24.0])

        def predict_survival_function(self, *_args, **_kwargs):  # pragma: no cover - must not be called
            raise AssertionError("out-of-range request must fail before prediction")

    with pytest.raises(InferenceAdapterError, match="baseline horizon"):
        cox_survival_estimates(ShortBaselineFitter(), np.zeros((1, 1)), ("feature",), "test")
