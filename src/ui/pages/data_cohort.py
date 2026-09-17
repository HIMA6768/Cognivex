"""Pending clinical/genomic cohort workspace."""

from __future__ import annotations

from ..components.layout import render_empty_state, render_page_header


def render() -> None:
    render_page_header(
        "Data / Cohort",
        "Review de-identified research cohort inputs and matching after ingestion is available.",
    )
    render_empty_state(
        "Dataset ingestion begins in R2",
        "No clinical or genomic file is loaded, and no source schema has been assumed.",
        "Complete the dataset handoff before adding CSV/TSV ingestion and patient/sample matching.",
    )
