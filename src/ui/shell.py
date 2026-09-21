"""Application shell and typed dispatch for the biomedical research prototype."""

from __future__ import annotations

from collections.abc import Callable, Mapping

import streamlit as st

from .components.layout import render_shell_status
from .components.oncomap import render_brand_mark
from .navigation import PAGE_ORDER, Page, render_navigation
from .pages import (
    cloud_integrated_subtype_classifier,
    data_cohort,
    gene_insights,
    methodology_about,
    model_comparison,
    overview,
    survival_analysis,
)
from .theme import apply_theme


PAGE_RENDERERS: Mapping[Page, Callable[[], None]] = {
    Page.OVERVIEW: overview.render,
    Page.SURVIVAL_ANALYSIS: survival_analysis.render,
    Page.MODEL_COMPARISON: model_comparison.render,
    Page.GENE_INSIGHTS: gene_insights.render,
    Page.CLOUD_SUBTYPE_CLASSIFIER: cloud_integrated_subtype_classifier.render,
    Page.DATA_COHORT: data_cohort.render,
    Page.METHODOLOGY_ABOUT: methodology_about.render_methodology,
    Page.ABOUT: methodology_about.render_about,
}

assert tuple(PAGE_RENDERERS) == PAGE_ORDER


RESEARCH_DISCLAIMER = (
    "Research and educational prototype only. This application is not a diagnostic medical "
    "device, treatment recommendation system, validated clinical prognosis system, or substitute "
    "for qualified oncology care. Do not use it for patient care."
)


def render_app() -> None:
    """Render the persistent shell and the selected pending-data page."""
    apply_theme()
    st.sidebar.markdown(
        '<div class="cv-sidebar-brand cv-sidebar-brand--with-mark">'
        '<span class="cv-sidebar-product-name">OncoMap</span>'
        '<p>Breast Cancer Prognosis &amp; Molecular Subtype Analysis</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    with st.sidebar:
        render_brand_mark()
        render_shell_status()
    selected_page = render_navigation()

    PAGE_RENDERERS[selected_page]()
    st.warning(RESEARCH_DISCLAIMER)