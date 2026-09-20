from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.artifacts.inference_registry import build_canonical_registry


ROOT = Path(__file__).resolve().parents[1]


def test_track_b_uses_persisted_raw75_to_model80_transform_only_contract() -> None:
    from src.inference.track_b import TrackBInferenceAdapter

    entry = build_canonical_registry(ROOT).track_b
    row = pd.read_csv(ROOT / "data/metabric/prepared/METABRIC_prepared.csv", nrows=1).iloc[0]
    adapter = TrackBInferenceAdapter(entry)
    result = adapter.predict({field: row[field] for field in entry.required_fields})

    assert len(adapter.required_fields) == 75
    assert len(adapter.model_feature_names) == 80
    assert result.output_kind == "log_partial_hazard"

