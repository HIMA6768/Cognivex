"""Session-state boundary for aggregate-only canonical cohort ingestion."""

from __future__ import annotations

from collections.abc import MutableMapping

from src.contracts import DataQualityReport, MetabricIngestionResult
from src.data.metabric import load_metabric
from src.data.metabric_quality import evaluate_metabric_quality


METABRIC_INGESTION_STATE_KEY = "metabric_ingestion_result"
METABRIC_QUALITY_STATE_KEY = "metabric_quality_report"
METABRIC_QUALITY_SOURCE_STATE_KEY = "metabric_quality_source"


def get_metabric_ingestion_state(
    session_state: MutableMapping[str, object], *, refresh: bool = False
) -> MetabricIngestionResult:
    """Reuse a validated aggregate result unless a user explicitly refreshes it."""
    existing = session_state.get(METABRIC_INGESTION_STATE_KEY)
    if refresh or not isinstance(existing, MetabricIngestionResult):
        existing = load_metabric()
        session_state[METABRIC_INGESTION_STATE_KEY] = existing
    return existing


def get_metabric_quality_state(
    session_state: MutableMapping[str, object],
    ingestion: MetabricIngestionResult,
    *,
    refresh: bool = False,
) -> DataQualityReport:
    """Reuse the aggregate R3 report until its validated R2 source is refreshed."""
    existing = session_state.get(METABRIC_QUALITY_STATE_KEY)
    source = session_state.get(METABRIC_QUALITY_SOURCE_STATE_KEY)
    if refresh or source is not ingestion or not isinstance(existing, DataQualityReport):
        existing = evaluate_metabric_quality(ingestion=ingestion)
        session_state[METABRIC_QUALITY_STATE_KEY] = existing
        session_state[METABRIC_QUALITY_SOURCE_STATE_KEY] = ingestion
    return existing
