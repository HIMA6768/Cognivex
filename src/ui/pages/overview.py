"""Research-prototype overview with no fabricated cohort results."""

from __future__ import annotations

from ..components.layout import render_empty_state, render_page_header


def render() -> None:
    render_page_header(
        "Overview",
        "A research workspace for comparing clinical and genomic breast-cancer analyses.",
    )
    render_empty_state(
        "Canonical cohort data is available",
        "R2 validates repository-owned METABRIC artifacts and exposes aggregate cohort information only.",
        "Open Data / Cohort to review the validated cohort. Modeling and patient-specific output remain out of scope.",
    )
