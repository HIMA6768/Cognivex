"""Unified OncoMap patient-analysis flow over the frozen public R9 service."""

from __future__ import annotations

from src.ui.analysis_service import get_analysis_service
import streamlit as st

from src.ui.components.oncomap import render_page_intro
from src.ui.components.patient_analysis import render_patient_analysis
from src.ui.components.results import render_patient_results


def render() -> None:
    render_page_intro("Patient Analysis", "Enter clinical details and an optional genomic profile to run the available frozen research analyses.")
    try:
        service = get_analysis_service()
    except Exception:
        st.error("ARTIFACT_UNAVAILABLE: Canonical analysis service is unavailable.")
        return
    if "oncomap_patient_response" in st.session_state and st.session_state.get("oncomap_patient_stage") == 5:
        render_patient_results(st.session_state["oncomap_patient_response"])
    else:
        render_patient_analysis(service)
