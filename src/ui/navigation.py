"""Typed metadata and grouped rendering for the OncoMap navigation shell."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import streamlit as st


class Page(str, Enum):
    """Approved R1 destinations in stable display order."""

    OVERVIEW = "overview"
    DATA_COHORT = "data_cohort"
    SURVIVAL_ANALYSIS = "survival_analysis"
    SUBTYPE_CLASSIFICATION = "subtype_classification"
    GENE_INSIGHTS = "gene_insights"
    MODEL_COMPARISON = "model_comparison"
    METHODOLOGY_ABOUT = "methodology_about"
    ABOUT = "about"


@dataclass(frozen=True, slots=True)
class PageSpec:
    """Display metadata required to dispatch a page renderer."""

    label: str
    renderer_key: str
    group: str


PAGE_ORDER: tuple[Page, ...] = (
    Page.OVERVIEW,
    Page.SURVIVAL_ANALYSIS,
    Page.MODEL_COMPARISON,
    Page.GENE_INSIGHTS,
    Page.DATA_COHORT,
    Page.METHODOLOGY_ABOUT,
    Page.ABOUT,
)

PAGE_SPECS: dict[Page, PageSpec] = {
    Page.OVERVIEW: PageSpec("Overview", "overview", "ONCOMAP"),
    Page.DATA_COHORT: PageSpec("Dataset", "data_cohort", "RESEARCH"),
    Page.SURVIVAL_ANALYSIS: PageSpec("Patient Analysis", "survival_analysis", "ANALYSIS"),
    Page.SUBTYPE_CLASSIFICATION: PageSpec(
        "Subtype Classification", "subtype_classification", "ANALYSIS"
    ),
    Page.GENE_INSIGHTS: PageSpec("Gene Insights", "gene_insights", "ANALYSIS"),
    Page.MODEL_COMPARISON: PageSpec("Model Evaluation", "model_comparison", "ANALYSIS"),
    Page.METHODOLOGY_ABOUT: PageSpec("Methodology", "methodology_about", "RESEARCH"),
    Page.ABOUT: PageSpec("About", "about", "RESEARCH"),
}


NAVIGATION_GROUPS: tuple[tuple[str, tuple[Page, ...]], ...] = (
    ("ONCOMAP", (Page.OVERVIEW,)),
    ("ANALYSIS", (Page.SURVIVAL_ANALYSIS, Page.MODEL_COMPARISON, Page.GENE_INSIGHTS)),
    ("RESEARCH", (Page.DATA_COHORT, Page.METHODOLOGY_ABOUT, Page.ABOUT)),
)

_SELECTED_PAGE_KEY = "oncomap_selected_page"


def _group_widget_key(group: str) -> str:
    return f"oncomap_navigation_{group.lower()}"


def _select_group_page(group: str) -> None:
    """Synchronize a one-of-many grouped navigation selection."""
    selected = st.session_state.get(_group_widget_key(group))
    if not isinstance(selected, Page):
        return
    st.session_state[_SELECTED_PAGE_KEY] = selected
    for other_group, _ in NAVIGATION_GROUPS:
        if other_group != group:
            st.session_state[_group_widget_key(other_group)] = None


def render_navigation() -> Page:
    """Render and return a rerun-stable page selection."""
    selected_page = st.session_state.get(_SELECTED_PAGE_KEY)
    if not isinstance(selected_page, Page) or selected_page not in PAGE_ORDER:
        selected_page = Page.OVERVIEW
        st.session_state[_SELECTED_PAGE_KEY] = selected_page

    for group, pages in NAVIGATION_GROUPS:
        index = pages.index(selected_page) if selected_page in pages else None
        st.sidebar.radio(
            group,
            pages,
            index=index,
            format_func=lambda page: PAGE_SPECS[page].label,
            key=_group_widget_key(group),
            on_change=_select_group_page,
            args=(group,),
        )
    return st.session_state[_SELECTED_PAGE_KEY]
