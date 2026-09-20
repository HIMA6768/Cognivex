"""Basic R10-A Streamlit integration for global R8 feature analysis."""

from __future__ import annotations

import streamlit as st

from src.ui.analysis_service import get_analysis_service
from src.ui.components.analysis import render_r8_analysis
from src.ui.components.layout import render_page_header


def render() -> None:
    render_page_header("Gene Insights", "Global model-associated coefficients from frozen R8; this is not patient-specific attribution or biological causality.")
    st.subheader("Global R8 prognostic feature analysis")
    try:
        render_r8_analysis(get_analysis_service().get_prognostic_feature_analysis())
    except Exception:
        st.error("ARTIFACT_UNAVAILABLE: Aggregate prognostic feature analysis is unavailable.")
