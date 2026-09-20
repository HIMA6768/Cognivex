from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.artifacts.inference_registry import build_canonical_registry
from src.contracts.inference import FROZEN_SUBTYPE_CLASS_ORDER


ROOT = Path(__file__).resolve().parents[1]


def test_track_c_returns_frozen_ordered_normalized_probabilities() -> None:
    from src.inference.track_c import TrackCInferenceAdapter

    entry = build_canonical_registry(ROOT).track_c
    row = pd.read_csv(ROOT / "data/metabric/prepared/METABRIC_prepared.csv", nrows=1).iloc[0]
    adapter = TrackCInferenceAdapter(entry)
    result = adapter.predict({field: row[field] for field in entry.required_fields})

    assert len(adapter.required_fields) == 68
    assert result.class_order == FROZEN_SUBTYPE_CLASS_ORDER
    assert result.predicted_class in FROZEN_SUBTYPE_CLASS_ORDER
    assert sum(result.probabilities) == pytest.approx(1.0, abs=1e-8)

