"""Research-prototype overview with no fabricated cohort results."""

from __future__ import annotations

from ..components.layout import render_empty_state, render_page_header


def render() -> None:
    render_page_header(
        "Overview",
        "A research workspace for comparing clinical and genomic breast-cancer analyses.",
    )
    render_empty_state(
        "No cohort has been loaded",
        "R1 provides the application shell only. No patient, cohort, model, or evaluation data is active.",
        "Proceed to Data / Cohort after R2 dataset ingestion is approved and implemented.",
    )
