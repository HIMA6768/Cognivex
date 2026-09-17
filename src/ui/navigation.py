"""Typed metadata and rendering for biomedical research navigation."""

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


@dataclass(frozen=True, slots=True)
class PageSpec:
    """Display metadata required to dispatch a page renderer."""

    label: str
    renderer_key: str


PAGE_ORDER: tuple[Page, ...] = (
    Page.OVERVIEW,
    Page.DATA_COHORT,
    Page.SURVIVAL_ANALYSIS,
    Page.SUBTYPE_CLASSIFICATION,
    Page.GENE_INSIGHTS,
    Page.MODEL_COMPARISON,
    Page.METHODOLOGY_ABOUT,
)

PAGE_SPECS: dict[Page, PageSpec] = {
    Page.OVERVIEW: PageSpec("Overview", "overview"),
    Page.DATA_COHORT: PageSpec("Data / Cohort", "data_cohort"),
    Page.SURVIVAL_ANALYSIS: PageSpec("Survival Analysis", "survival_analysis"),
    Page.SUBTYPE_CLASSIFICATION: PageSpec(
        "Subtype Classification", "subtype_classification"
    ),
    Page.GENE_INSIGHTS: PageSpec("Gene Insights", "gene_insights"),
    Page.MODEL_COMPARISON: PageSpec("Model Comparison", "model_comparison"),
    Page.METHODOLOGY_ABOUT: PageSpec("Methodology / About", "methodology_about"),
}


def render_navigation() -> Page:
    """Render and return a rerun-stable page selection."""
    return st.sidebar.radio(
        "Navigation",
        PAGE_ORDER,
        format_func=lambda page: PAGE_SPECS[page].label,
        key="primary_navigation",
    )
