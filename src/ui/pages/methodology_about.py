"""Concise methodology and prototype context pages for OncoMap."""

from __future__ import annotations

import streamlit as st

from ..components.oncomap import render_page_intro, render_workflow_steps


def render_methodology() -> None:
    render_page_intro("Methodology", "Understand the research workflow in under one minute.")
    st.subheader("Analysis pipeline")
    render_workflow_steps(("Input", "Prognosis Analysis", "Molecular Subtype", "Results"))
    columns = st.columns(4)
    for column, title, body in zip(
        columns,
        ("Track A", "Track B", "Track C", "R8"),
        (
            "Clinical prognosis using Cox proportional hazards.",
            "Clinical + genomic prognosis using penalized Cox proportional hazards.",
            "Molecular subtype classification using a frozen Random Forest.",
            "Global genomic model-association analysis.",
        ),
        strict=True,
    ):
        with column:
            st.markdown(f"**{title}**")
            st.caption(body)
    with st.expander("Research interpretation boundary"):
        st.markdown("Outputs are research-model associations and predictions. They are not diagnostic conclusions, treatment recommendations, or evidence of causality.")


def render_about() -> None:
    render_page_intro("About", "OncoMap is a hackathon research prototype built on the METABRIC cohort.")
    st.subheader("Purpose")
    st.markdown("Explore modeled survival, molecular subtype, and global genomic associations using frozen research artifacts.")
    st.subheader("What the outputs mean")
    st.markdown("Prognosis and subtype outputs are model estimates. Genomic insights summarize global model associations, not patient-specific explanations.")
    st.subheader("Limitations")
    st.markdown("This is not a clinical decision system, has no external validation claim, and must not guide patient care or treatment.")


def render() -> None:
    """Preserve the historical renderer entry point for callers outside the active route map."""
    render_methodology()
