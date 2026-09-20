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


def render_brand_mark(*, decorative: bool = False) -> None:
    """Render a package-owned inline DNA mark without external assets."""
    size = "116" if decorative else "28"
    aria = 'aria-hidden="true"' if decorative else 'aria-label="OncoMap DNA mark" role="img"'
    st.markdown(
        f'''<svg class="cv-dna-mark" width="{size}" height="{size}" viewBox="0 0 120 120" {aria} xmlns="http://www.w3.org/2000/svg">
        <path d="M36 10c42 20 42 80 0 100M84 10c-42 20-42 80 0 100" fill="none" stroke="#0F9E9A" stroke-width="8" stroke-linecap="round"/>
        <path d="M43 27h34M52 49h16M52 71h16M43 93h34" stroke="#2563EB" stroke-width="7" stroke-linecap="round"/>
        <circle cx="60" cy="10" r="5" fill="#2563EB"/><circle cx="60" cy="110" r="5" fill="#0F9E9A"/>
        </svg>''',
        unsafe_allow_html=True,
    )
