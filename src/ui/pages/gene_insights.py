"""Pending gene-level model-insight workspace."""

from __future__ import annotations

from ..components.layout import render_empty_state, render_page_header


def render() -> None:
    render_page_header(
        "Gene Insights",
        "Separate model-associated feature importance from biological support.",
    )
    render_empty_state(
        "Gene-level insights are pending evaluated model outputs",
        "No gene ranking, coefficient, feature importance, or biological claim is available.",
        "Complete model evaluation before interpreting gene-level associations conservatively.",
    )
