"""Streamlit-only cached access to the frozen R9 public service boundary."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.services.analysis import AnalysisService


def repository_root() -> Path:
    """Return the repository root independent of the deployment machine."""
    return Path(__file__).resolve().parents[2]


@st.cache_resource(show_spinner=False)
def get_analysis_service(root: Path | None = None) -> AnalysisService:
    """Construct the trusted R9 service once per Streamlit resource cache."""
    return AnalysisService.from_canonical_artifacts(repository_root() if root is None else Path(root))
