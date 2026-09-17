"""Pending molecular-subtype classification workspace."""

from __future__ import annotations

from ..components.layout import render_empty_state, render_page_header


def render() -> None:
    render_page_header(
        "Subtype Classification",
        "Evaluate a future multi-class classifier using verified gene-expression labels.",
    )
    render_empty_state(
        "Subtype classification is pending gene-expression data and confirmed dataset labels",
        "Exact subtype labels will be taken from the selected dataset after handoff.",
        "Inspect the dataset taxonomy before freezing labels or training a classifier.",
    )
