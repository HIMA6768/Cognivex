"""Pending clinical-versus-genomic model-comparison page."""

from __future__ import annotations

from ..components.layout import render_empty_state, render_page_header


def render() -> None:
    """Show no values until matched, censoring-aware evaluation is available."""
    render_page_header(
        "Model Comparison",
        "Compare clinical-only and clinical-plus-genomic prognosis after real evaluation.",
    )
    render_empty_state(
        "Evaluation pending model handoff",
        "No C-index, improvement delta, classification metric, or model ranking is available.",
        "Use the same verified cohort and evaluation strategy before comparing models.",
    )
