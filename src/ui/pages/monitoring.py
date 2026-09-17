"""Zero-data monitoring placeholder for the development prototype."""

from __future__ import annotations

from ..components.layout import render_empty_state, render_page_header


def render() -> None:
    """Show the honest zero-data state without fabricated traffic or metrics."""
    render_page_header(
        "Monitoring",
        "Development readiness will be visible here once monitoring is connected.",
    )
    render_empty_state(
        "Development state",
        "No monitoring data is available in this development prototype.",
        "Monitoring remains intentionally empty until a future integration is approved.",
    )
