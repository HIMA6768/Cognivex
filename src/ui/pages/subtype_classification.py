"""Basic R10-A Streamlit integration for frozen R9 Track C."""

from __future__ import annotations

import streamlit as st

from src.contracts.inference import AnalysisTrack
from src.ui.analysis_service import get_analysis_service
from src.ui.components.analysis import render_genomic_input, render_request_errors, render_track_outcome, submit_track_request
from src.ui.components.layout import render_page_header


def render() -> None:
    render_page_header("Subtype Classification", "Run the frozen six-class R9 subtype classifier using optional exact-contract genomic inputs.")
    try:
        service = get_analysis_service()
    except Exception:
        st.error("ARTIFACT_UNAVAILABLE: Canonical analysis service is unavailable.")
        return
    fields = service.registry.track_c.required_fields
    with st.form("track_c_form"):
        st.subheader("Track C genomic input")
        values = render_genomic_input(fields, key_prefix="track_c", numeric_fields=fields[:50])
        submitted = st.form_submit_button("Run Track C")
    if submitted:
        response = submit_track_request(service, AnalysisTrack.TRACK_C, values)
        render_request_errors(response.request_errors)
        for outcome in response.outcomes:
            render_track_outcome(outcome)
