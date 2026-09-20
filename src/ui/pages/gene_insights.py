"""Aggregate-only R8 genomic association presentation for OncoMap."""

from __future__ import annotations

import streamlit as st

from src.ui.analysis_service import get_analysis_service
from src.ui.components.charts import render_named_bar_chart
from src.ui.components.oncomap import render_metric_card, render_page_intro


def render() -> None:
    render_page_intro("Gene Insights", "Global model-associated coefficients from frozen R8. These are not causal findings or patient-specific attributions.")
    try:
        outcome = get_analysis_service().get_prognostic_feature_analysis()
        if outcome.error is not None:
            st.error(f"{outcome.error.code}: {outcome.error.message}")
            return
        assert outcome.view is not None
        effects = outcome.view.effects
        active = tuple(item.effect for item in effects if item.effect.is_active)
        summary = st.columns(3)
        for column, label, value in zip(summary, ("Analyzed", "Active", "Near-zero"), (len(effects), len(active), len(effects) - len(active)), strict=True):
            with column:
                render_metric_card(label, str(value))
        st.subheader("Strongest model-associated features")
        ranked = tuple(sorted(active, key=lambda effect: effect.rank))[:12]
        render_named_bar_chart(((effect.raw_feature_name, effect.abs_beta) for effect in ranked), value_label="Absolute coefficient")
        st.caption("Direction labels describe higher modeled hazard, lower modeled hazard, or effectively zero association under the frozen R8 threshold.")
        with st.expander("View all genomic features"):
            st.dataframe(
                {
                    "Rank": [item.effect.rank for item in effects],
                    "Feature": [item.effect.raw_feature_name for item in effects],
                    "Association": [item.effect.direction_display for item in effects],
                    "Status": ["Active" if item.effect.is_active else "Near-zero" for item in effects],
                    "Coefficient": [item.effect.beta for item in effects],
                },
                hide_index=True,
                width="stretch",
            )
    except Exception:
        st.error("ARTIFACT_UNAVAILABLE: Aggregate prognostic feature analysis is unavailable.")
