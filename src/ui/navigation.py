"""Typed metadata and rendering for the application's stable navigation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import streamlit as st


class Page(str, Enum):
    """Destinations available in the pre-model application shell."""

    ASSESSMENT = "assessment"
    MODEL_COMPARISON = "model_comparison"
    MODEL_INSIGHTS = "model_insights"
    MONITORING = "monitoring"
    SYSTEM_ABOUT = "system_about"


@dataclass(frozen=True)
class PageSpec:
    """Display metadata required to dispatch a page renderer."""

    label: str
    renderer_key: str


PAGE_ORDER: tuple[Page, ...] = (
    Page.ASSESSMENT,
    Page.MODEL_COMPARISON,
    Page.MODEL_INSIGHTS,
    Page.MONITORING,
    Page.SYSTEM_ABOUT,
)

PAGE_SPECS: dict[Page, PageSpec] = {
    Page.ASSESSMENT: PageSpec("Assessment", "assessment"),
    Page.MODEL_COMPARISON: PageSpec("Model Comparison", "model_comparison"),
    Page.MODEL_INSIGHTS: PageSpec("Model Insights", "model_insights"),
    Page.MONITORING: PageSpec("Monitoring", "monitoring"),
    Page.SYSTEM_ABOUT: PageSpec("System / About", "system_about"),
}


def render_navigation() -> Page:
    """Render and return the current page selection with rerun-stable state."""
    return st.sidebar.radio(
        "Navigation",
        PAGE_ORDER,
        format_func=lambda page: PAGE_SPECS[page].label,
        key="primary_navigation",
    )
