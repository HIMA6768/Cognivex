from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.contracts.inference import AnalysisRequest, AnalysisTrack, TrackReadinessState
from src.services.analysis import AnalysisService


ROOT = Path(__file__).resolve().parents[1]


def _row_features(service: AnalysisService) -> dict[str, object]:
    row = pd.read_csv(ROOT / "data/metabric/prepared/METABRIC_prepared.csv", nrows=1).iloc[0]
    return {field: row[field] for field in service.allowed_input_fields}


def test_unknown_field_is_global_and_runs_no_track() -> None:
    service = AnalysisService.from_canonical_artifacts(ROOT)
    response = service.analyze(AnalysisRequest({**_row_features(service), "Tumor_Size": 4.0}))

    assert response.request_errors[0].code == "UNKNOWN_FIELD"
    assert response.outcomes == ()
    assert service.adapter_call_counts == {track: 0 for track in AnalysisTrack}


def test_clinical_only_has_independent_readiness() -> None:
    service = AnalysisService.from_canonical_artifacts(ROOT)
    clinical = {field: _row_features(service)[field] for field in service.registry.track_a.required_fields}
    response = service.analyze(AnalysisRequest(clinical))

    assert tuple(item.state for item in response.outcomes) == (
        TrackReadinessState.READY,
        TrackReadinessState.MISSING_REQUIRED_FIELDS,
        TrackReadinessState.MISSING_REQUIRED_FIELDS,
    )
