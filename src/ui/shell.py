"""Application shell and typed dispatch for the Streamlit prototype."""

from __future__ import annotations

from collections.abc import Callable, Mapping

import streamlit as st

from .components.layout import render_shell_status
from .navigation import Page, render_navigation
from .pages import assessment, model_comparison, model_insights, monitoring, system_about
from .theme import apply_theme


PAGE_RENDERERS: Mapping[Page, Callable[[], None]] = {
    Page.ASSESSMENT: assessment.render,
    Page.MODEL_COMPARISON: model_comparison.render,
    Page.MODEL_INSIGHTS: model_insights.render,
    Page.MONITORING: monitoring.render,
    Page.SYSTEM_ABOUT: system_about.render,
}


def render_app() -> None:
    """Render the persistent product shell and the currently selected page."""
    apply_theme()
    st.sidebar.markdown(
        "<div class=\"cv-sidebar-brand\">"
        "<span class=\"cv-sidebar-product-name\">Auto Insurance Damage Assessment</span>"
        "<p>AI-assisted vehicle damage triage</p>"
        "</div>",
        unsafe_allow_html=True,
    )
    with st.sidebar:
        render_shell_status()
    selected_page = render_navigation()

    PAGE_RENDERERS[selected_page]()
    st.info(
        "Decision-support only: this prototype does not make coverage, repair, "
        "or claim decisions."
    )
