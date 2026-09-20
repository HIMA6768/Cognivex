"""Judge-facing aggregate overview for the OncoMap research workspace."""

from __future__ import annotations

import streamlit as st

from ..analysis_service import get_analysis_service
from ..components.oncomap import (
    render_brand_mark,
    render_metric_card,
    render_page_intro,
    render_status_badge,
    render_workflow_steps,
)
from ..navigation import Page, navigate_to


def render() -> None:
    hero, decoration = st.columns((4, 1))
    with hero:
        render_page_intro("OncoMap", "Breast Cancer Prognosis & Molecular Subtype Analysis")
        st.markdown("Combine clinical and genomic data to explore modeled survival, molecular subtype, and global genomic associations.")
        st.caption("Research Prototype")
        st.button("Analyze a Patient →", type="primary", on_click=navigate_to, args=(Page.SURVIVAL_ANALYSIS,))
    with decoration:
        render_brand_mark(decorative=True)

    cards = st.columns(4)
    for column, label, value, detail in zip(
        cards,
        ("METABRIC patients", "Genomic features", "Prognosis models", "Subtype classes"),
        ("1,904", "68", "2", "6"),
        ("Prepared research cohort", "Frozen model contract", "Clinical and clinical + genomic", "Frozen molecular taxonomy"),
        strict=True,
    ):
        with column:
            render_metric_card(label, value, detail)

    st.subheader("Analysis workflow")
    render_workflow_steps(("Clinical + Genomic Data", "Prognosis Analysis", "Molecular Subtype", "Genomic Insights"))

    st.subheader("Model availability")
    try:
        registry = get_analysis_service().registry
        statuses = (
            ("Track A — Clinical Cox", registry.track_a.available),
            ("Track B — Clinical + Genomic Cox", registry.track_b.available),
            ("Track C — Molecular Subtype Classification", registry.track_c.available),
            ("R8 — Global Genomic Associations", registry.r8.available),
        )
        columns = st.columns(4)
        for column, (label, ready) in zip(columns, statuses, strict=True):
            with column:
                render_status_badge(label, ready=ready)
                st.caption(f"{label} — {'READY' if ready else 'UNAVAILABLE'}")
    except Exception:
        st.warning("Model availability is temporarily unavailable. Patient analysis remains governed by safe R9 readiness states.")
    st.caption("Research prototype only. Outputs are model-based research estimates, not clinical recommendations.")
