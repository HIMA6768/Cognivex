from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.artifacts.inference_registry import build_canonical_registry


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

