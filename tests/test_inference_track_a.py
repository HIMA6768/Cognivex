from __future__ import annotations

from pathlib import Path

import pandas as pd
import numpy as np

from src.artifacts.inference_registry import build_canonical_registry
from src.inference._common import ordered_frame


ROOT = Path(__file__).resolve().parents[1]


def test_track_a_predicts_a_finite_log_relative_hazard_from_exact_raw_contract() -> None:
    from src.inference.track_a import TrackAInferenceAdapter

    entry = build_canonical_registry(ROOT).track_a
    row = pd.read_csv(ROOT / "data/metabric/prepared/METABRIC_prepared.csv", nrows=1).iloc[0]
    adapter = TrackAInferenceAdapter(entry)
    result = adapter.predict({field: row[field] for field in entry.required_fields})

    assert result.output_kind == "log_partial_hazard"
    assert result.lineage.track.value == "track_a"
    assert len(adapter.required_fields) == 7


def test_track_a_returns_frozen_survival_estimates_without_changing_log_hazard() -> None:
    from src.inference.track_a import TrackAInferenceAdapter

    entry = build_canonical_registry(ROOT).track_a
    adapter = TrackAInferenceAdapter(entry)
    synthetic_features = {
        "age_at_diagnosis": 55.0,
        "tumor_size": 2.0,
        "tumor_stage": "2",
        "lymph_nodes_examined_positive": 1.0,
        "er_status_measured_by_ihc": "Positive",
        "pr_status": "Positive",
        "her2_status": "Negative",
    }
    result = adapter.predict(synthetic_features)
    matrix = entry.preprocessor.transform(ordered_frame(
        synthetic_features,
        entry.required_fields,
        categorical_fields=("tumor_stage", "er_status_measured_by_ihc", "pr_status", "her2_status"),
    ))
    expected_score = float(entry.model.predict_risk(matrix)[0])
    expected_survival = entry.model.fitter.predict_survival_function(
        pd.DataFrame(np.asarray(matrix, dtype=float), columns=entry.model.feature_names),
        times=[12.0, 36.0, 60.0],
    ).iloc[:, 0].to_numpy(dtype=float)

    assert result.value == expected_score
    assert result.survival_estimates is not None
    assert np.allclose(
        (
            result.survival_estimates.survival_probability_1y,
            result.survival_estimates.survival_probability_3y,
            result.survival_estimates.survival_probability_5y,
        ),
        expected_survival,
        rtol=0,
        atol=1e-12,
    )
