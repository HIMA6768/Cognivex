"""Basic R10-A Streamlit integration for R9 survival tracks."""

from __future__ import annotations

import streamlit as st

from src.contracts.inference import AnalysisTrack
from src.ui.analysis_service import get_analysis_service
from src.ui.components.analysis import render_clinical_inputs, render_genomic_input, render_request_errors, render_track_outcome, submit_track_request
from src.ui.components.layout import render_page_header

_CLINICAL_NUMERIC = ("age_at_diagnosis", "tumor_size", "lymph_nodes_examined_positive")
_CLINICAL_NULLABLE = ("tumor_size", "er_status_measured_by_ihc")


def _service_or_error():
    try:
        return get_analysis_service()
    except Exception:
        st.error("ARTIFACT_UNAVAILABLE: Canonical analysis service is unavailable.")
        return None


def _submit(track: AnalysisTrack, values: dict[str, str | float | None]) -> None:
    service = _service_or_error()
    if service is None:
        return
    response = submit_track_request(service, track, values)
    render_request_errors(response.request_errors)
    for outcome in response.outcomes:
        render_track_outcome(outcome)


def render() -> None:
    render_page_header("Survival Analysis", "Run only the frozen R9 research-model outputs; no survival probability or clinical risk category is shown.")
    service = _service_or_error()
    if service is None:
        return
    track_a_fields = service.registry.track_a.required_fields
    track_b_fields = service.registry.track_b.required_fields
    track_c_fields = service.registry.track_c.required_fields
    expression_fields = track_c_fields[:50]
    tab_a, tab_b = st.tabs(("Track A", "Track B"))
    with tab_a:
        st.subheader("Track A clinical input")
        with st.form("track_a_form"):
            values = render_clinical_inputs(track_a_fields, key_prefix="track_a", numeric_fields=_CLINICAL_NUMERIC, nullable_fields=_CLINICAL_NULLABLE)
            submitted = st.form_submit_button("Run Track A")
        if submitted:
            _submit(AnalysisTrack.TRACK_A, values)
    with tab_b:
        st.subheader("Track B clinical + genomic input")
        with st.form("track_b_form"):
            values = render_clinical_inputs(track_a_fields, key_prefix="track_b", numeric_fields=_CLINICAL_NUMERIC, nullable_fields=_CLINICAL_NULLABLE)
            values.update(render_genomic_input(track_b_fields[7:], key_prefix="track_b", numeric_fields=expression_fields))
            submitted = st.form_submit_button("Run Track B")
        if submitted:
            _submit(AnalysisTrack.TRACK_B, values)
