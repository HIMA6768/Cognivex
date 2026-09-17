"""Methodology, safety boundary, and pending research plan."""

from __future__ import annotations

import streamlit as st

from ..components.layout import render_page_header


def render() -> None:
    render_page_header(
        "Methodology / About",
        "Scope, scientific comparison, and safety boundaries for the Cognivex prototype.",
    )
    st.subheader("Primary research question")
    st.markdown(
        "Clinical-only versus clinical-plus-genomic prognosis: quantify any improvement only "
        "after a censoring-aware evaluation on a verified cohort."
    )
    st.subheader("Separate analytical tasks")
    st.markdown(
        "Survival prognosis, molecular subtype classification, and gene-level model insight are "
        "separate tasks. R1 contains no dataset or model results for any task."
    )
    st.subheader("Interpretation boundary")
    st.markdown(
        "Future model-associated gene importance must be distinguished from independent "
        "biological support and must not be presented as causality."
    )
