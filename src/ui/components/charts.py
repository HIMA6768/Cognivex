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
    st.bar_chart(frame, stack=False, width="stretch")


def render_probability_bars(rows: Iterable[tuple[str, float]]) -> None:
    """Render fixed-order probabilities as readable one-decimal horizontal bars."""
    for label, probability in rows:
        left, right = st.columns((4, 1))
        with left:
            st.markdown(f"**{label}**")
        with right:
            st.markdown(f"{probability * 100:.1f}%")
        st.progress(min(max(float(probability), 0.0), 1.0))


def render_ranked_coefficient_chart(rows: Iterable[tuple[str, float, str]]) -> None:
    """Render ordered global coefficients with an explicit non-causal direction label."""
    frame = pd.DataFrame(rows, columns=("Feature", "Coefficient", "Association"))
    st.bar_chart(
        frame.set_index("Feature")[["Coefficient"]],
        horizontal=True,
        sort=False,
        width="stretch",
    )
    st.dataframe(
        {
            "Feature": frame["Feature"],
            "Coefficient": frame["Coefficient"].map(lambda value: f"{value:.3f}"),
            "Association": frame["Association"],
        },
        hide_index=True,
        width="stretch",
    )
