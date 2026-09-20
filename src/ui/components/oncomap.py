"""Presentation-only primitives shared by the OncoMap Streamlit pages."""

from __future__ import annotations

from html import escape
from collections.abc import Iterable

import streamlit as st


def render_page_intro(title: str, subtitle: str) -> None:
    """Render a high-hierarchy OncoMap page introduction."""
    st.title(title)
    st.caption(subtitle)


def render_metric_card(label: str, value: str, detail: str = "") -> None:
    """Render a static card without interpreting or transforming its value."""
    detail_html = f"<p>{escape(detail)}</p>" if detail else ""
    st.markdown(
        '<section class="cv-metric-card">'
        f'<div class="cv-metric-card__value">{escape(str(value))}</div>'
        f'<div class="cv-metric-card__label">{escape(label)}</div>'
        f"{detail_html}</section>",
        unsafe_allow_html=True,
    )


def render_status_badge(label: str, *, ready: bool) -> None:
    """Render an availability badge, not a model-quality assertion."""
    state = "ready" if ready else "unavailable"
    text = "Ready" if ready else "Unavailable"
    st.markdown(
        f'<span class="cv-status-badge cv-status-badge--{state}">{escape(label)} · {text}</span>',
        unsafe_allow_html=True,
    )


def render_workflow_steps(steps: Iterable[str]) -> None:
    """Render an ordered, presentation-only analysis workflow."""
    st.markdown(" → ".join(escape(step) for step in steps))


def render_research_disclaimer() -> None:
    """Render the concise fixed-horizon survival interpretation boundary."""
    st.caption(
        "Model-estimated survival probability from the frozen METABRIC Cox model. "
        "Research use only; not a clinically validated prognosis or treatment recommendation."
    )
