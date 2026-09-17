"""Pending survival-analysis workspace."""

from __future__ import annotations

from ..components.layout import render_empty_state, render_page_header


def render() -> None:
    render_page_header(
        "Survival Analysis",
        "Compare a clinical baseline with a clinical-plus-genomic prognosis model.",
    )
    render_empty_state(
        "Survival analysis is pending validated cohort data and model handoff",
        "No survival endpoint, censoring definition, fitted model, or evaluation result is available.",
        "Validate the selected cohort and leak-safe evaluation design before fitting any model.",
    )
