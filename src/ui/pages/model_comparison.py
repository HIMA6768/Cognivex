"""Pending model-comparison placeholder."""

from __future__ import annotations

from ..components.layout import render_empty_state, render_page_header


def render() -> None:
    """Explain that comparison data will arrive only after evaluation is available."""
    render_page_header(
        "Model Comparison",
        "Compare candidate model evaluations when validated results become available.",
    )
    render_empty_state(
        "Comparison pending",
        "Model evaluation results are pending.",
        "Complete a future evaluation workflow to populate this view.",
    )
