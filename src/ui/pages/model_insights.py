"""Unavailable-insights placeholder for the pre-model prototype."""

from __future__ import annotations

from ..components.layout import render_empty_state, render_page_header


def render() -> None:
    """Keep insights unavailable until a future evaluation produces evidence."""
    render_page_header(
        "Model Insights",
        "Explore evaluation evidence when model results are available.",
    )
    render_empty_state(
        "Insights unavailable",
        "Evaluation results are not available yet.",
        "Return after a future evaluation workflow has produced results.",
    )
