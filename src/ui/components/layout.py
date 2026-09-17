"""Safe, reusable Streamlit layout helpers."""

from __future__ import annotations

from html import escape

import streamlit as st


def render_page_header(title: str, subtitle: str) -> None:
    """Render a consistent text-only header for a page."""
    st.title(title)
    st.caption(subtitle)


def render_empty_state(title: str, message: str, next_step: str) -> None:
    """Explain a missing data state and its next safe action."""
    surface_html = (
        '<section class="cv-surface" role="status">'
        f"<h2>{escape(title)}</h2>"
        f"<p>{escape(message)}</p>"
        f"<p><strong>Next:</strong> {escape(next_step)}</p>"
        "</section>"
    )
    st.markdown(surface_html, unsafe_allow_html=True)


def render_shell_status() -> None:
    """Render a high-contrast, text-and-shape research status indicator."""
    st.markdown(
        '<div class="cv-status-pill" role="status">'
        '<span aria-hidden="true">●</span> Research prototype</div>',
        unsafe_allow_html=True,
    )
