"""System context for the pre-model assessment prototype."""

from __future__ import annotations

import streamlit as st

from ..components.layout import render_page_header


def render() -> None:
    """Describe the planned flow, evaluation scope, and current limitations."""
    render_page_header(
        "System / About",
        "A pre-model prototype for transparent vehicle-damage assessment planning.",
    )
    st.subheader("Application flow")
    st.markdown(
        "Upload -> Validation -> Quality Gate -> Classifier -> YOLO localization "
        "-> Decision Engine -> Routing"
    )
    st.subheader("Model families under evaluation")
    st.markdown(
        "Candidate models under evaluation: Custom CNN, MobileNetV2, and ViT-Tiny."
    )
    st.markdown(
        "Planned localization: YOLOv8n. Evaluation results are unavailable. "
        "Final selection is Pending AI model handoff."
    )
    st.subheader("Known limitations")
    st.markdown(
        "This prototype has no image upload, model execution, decisioning, or "
        "operational data. It is decision support only and cannot determine a claim outcome."
    )
