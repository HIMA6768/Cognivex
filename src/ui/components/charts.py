"""Native Streamlit charts for approved aggregate and service-result views."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd
import streamlit as st


def render_named_bar_chart(rows: Iterable[tuple[str, float]], *, value_label: str) -> None:
    """Render an ordered horizontal bar chart without reordering input rows."""
    frame = pd.DataFrame(rows, columns=("Label", value_label))
    st.bar_chart(frame, x=value_label, y="Label", horizontal=True, sort=False, width="stretch")


def render_metric_comparison_chart(rows: Iterable[tuple[str, float, float]]) -> None:
    """Render validation/test aggregate C-index values as a grouped native chart."""
    frame = pd.DataFrame(rows, columns=("Model", "Validation", "Test")).set_index("Model")
    st.bar_chart(frame, width="stretch")
