"""Session-state boundary for aggregate-only canonical cohort ingestion."""

from __future__ import annotations

from collections.abc import MutableMapping

from src.contracts import MetabricIngestionResult
from src.data.metabric import load_metabric


METABRIC_INGESTION_STATE_KEY = "metabric_ingestion_result"


def get_metabric_ingestion_state(
    session_state: MutableMapping[str, object], *, refresh: bool = False
) -> MetabricIngestionResult:
    """Reuse a validated aggregate result unless a user explicitly refreshes it."""
    existing = session_state.get(METABRIC_INGESTION_STATE_KEY)
    if refresh or not isinstance(existing, MetabricIngestionResult):
        existing = load_metabric()
        session_state[METABRIC_INGESTION_STATE_KEY] = existing
    return existing
