"""Research-prototype overview with no fabricated cohort results."""

from __future__ import annotations

from ..components.layout import render_empty_state, render_page_header


def render() -> None:
    render_page_header(
        "Overview",
        "A research workspace for comparing clinical and genomic breast-cancer analyses.",
    )
    render_empty_state(
        "Canonical cohort quality is available",
        "R3 adds aggregate engineering-quality findings to R2's repository-owned METABRIC validation.",
        "Open Data / Cohort to review the validated cohort and its data-quality limitations. Modeling and patient-specific output remain out of scope.",
    )
