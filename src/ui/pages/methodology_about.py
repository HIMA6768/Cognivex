"""Concise research workflow and prototype context pages for OncoMap."""

from __future__ import annotations

import streamlit as st

from ..components.oncomap import render_metric_card, render_page_intro, render_status_badge, render_workflow_steps
from ..navigation import Page, navigate_to


def _track_card(title: str, detail: str) -> None:
    st.markdown(f"**{title}**")
    st.caption(detail)


def render_methodology() -> None:
    render_page_intro(
        "Methodology",
        "How OncoMap transforms clinical and genomic inputs into research-model outputs.",
    )
    st.subheader("Research workflow")
    render_workflow_steps(("Patient Inputs", "Validation + Frozen Preprocessing", "Analysis Models", "Research Outputs"))
    st.subheader("Analysis tracks")
    columns = st.columns(4)
    cards = (
        ("Track A", "7 clinical · Cox proportional hazards · log relative hazard · 1/3/5-year model-estimated survival"),
        ("Track B", "7 clinical + 50 expression + 18 mutation · 75 total raw fields · penalized Cox proportional hazards · 1/3/5-year survival"),
        ("Track C", "50 expression + 18 mutation · Random Forest · six molecular subtype probabilities"),
        ("R8", "Frozen Track B coefficients · global/aggregate only · 68 model-associated effects"),
    )
    for column, (title, detail) in zip(columns, cards, strict=True):
        with column:
            _track_card(title, detail)
    st.subheader("Quality principles")
    quality_columns = st.columns(5)
    for column, label, detail in zip(
        quality_columns,
        ("Leak-safe", "Locked split", "Frozen artifacts", "Private inputs", "Censoring-aware"),
        ("Training-only preprocessing", "Consistent train / validation / test cohorts", "Checksum-verified research bundles", "No patient persistence", "Survival models respect censoring"),
        strict=True,
    ):
        with column:
            render_metric_card(label, "✓", detail)
    with st.expander("View technical methodology"):
        st.markdown("Clinical fields use frozen, train-fitted preprocessing. Selected expression and mutation fields follow the approved model contracts. R9 validates artifacts before serving in-memory research outputs.")
        st.caption("The locked split supports development and held-out evaluation; it does not establish external clinical validation.")
    st.warning("Research boundary: outputs are research-model associations and predictions, not diagnostic conclusions, treatment recommendations, or evidence of causality.")


def render_about() -> None:
    render_page_intro("OncoMap", "Breast Cancer Prognosis & Molecular Subtype Analysis")
    st.markdown("Research prototype combining clinical and genomic data to explore modeled survival, molecular subtype, and genomic associations.")
    render_status_badge("Research Prototype", ready=True)
    cta, methodology = st.columns(2)
    cta.button("Analyze a Patient", type="primary", on_click=navigate_to, args=(Page.SURVIVAL_ANALYSIS,))
    methodology.button("View Methodology", on_click=navigate_to, args=(Page.METHODOLOGY_ABOUT,))
    summary = st.columns(3)
    for column, label, value, detail in zip(
        summary,
        ("METABRIC patients", "Analysis tracks", "Genomic model inputs"),
        ("1,904", "3", "68"),
        ("Prepared research cohort", "A, B, and C", "50 expression + 18 mutation"),
        strict=True,
    ):
        with column:
            render_metric_card(label, value, detail)
    st.subheader("About this prototype")
    cards = st.columns(3)
    for column, title, detail in zip(
        cards,
        ("Purpose", "What it analyzes", "What it produces"),
        ("A judge-friendly research workspace for exploring frozen METABRIC models.", "Clinical and selected genomic inputs for prognosis and molecular subtype analysis.", "Model-estimated survival, subtype probabilities, and global genomic associations."),
        strict=True,
    ):
        with column:
            _track_card(title, detail)
    st.subheader("From data to research outputs")
    render_workflow_steps(("Clinical + Genomic Data", "Frozen Research Models", "Prognosis + Subtype", "Genomic Insights"))
    st.warning("Research Limitations — OncoMap is not a clinical decision system, has no external-validation claim, and must not guide patient care or treatment.")
    st.subheader("Project information")
    st.markdown(" · ".join(("**Dataset:** METABRIC", "**Prognosis:** Cox proportional hazards", "**Subtype:** Random Forest", "**Interface:** Streamlit", "**Status:** Hackathon research prototype")))


def render() -> None:
    """Preserve the historical renderer entry point for callers outside the active route map."""
    render_methodology()
