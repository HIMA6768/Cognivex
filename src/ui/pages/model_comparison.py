"""Aggregate-only frozen evaluation evidence for OncoMap."""

from __future__ import annotations

import streamlit as st

from ..analysis_service import get_analysis_service
from ..components.charts import render_metric_comparison_chart
from ..components.oncomap import render_metric_card, render_page_intro


def render_model_evaluation(service) -> None:
    """Render only the aggregate R9 projection, never a metric artifact directly."""
    outcome = service.get_model_evaluation()
    if outcome.error is not None:
        st.error(f"{outcome.error.code}: {outcome.error.message}")
        return
    assert outcome.view is not None
    view = outcome.view
    st.subheader("Prognosis evaluation")
    cards = st.columns(3)
    with cards[0]:
        render_metric_card(
            "Track A — Clinical Cox",
            f"{view.track_a.test_c_index:.3f}",
            f"Test C-index · Validation {view.track_a.validation_c_index:.3f}",
        )
    with cards[1]:
        render_metric_card(
            "Track B — Clinical + Genomic Cox",
            f"{view.track_b.test_c_index:.3f}",
            f"Test C-index · Validation {view.track_b.validation_c_index:.3f}",
        )
    with cards[2]:
        render_metric_card("Test difference", f"{view.test_delta:+.3f}", "Track B minus Track A")
    render_metric_comparison_chart((
        ("Track A", view.track_a.validation_c_index, view.track_a.test_c_index),
        ("Track B", view.track_b.validation_c_index, view.track_b.test_c_index),
    ))
    st.info(view.interpretation)

    st.subheader("Track C — Molecular subtype classification")
    subtype_columns = st.columns(4)
    for column, label, value in zip(
        subtype_columns,
        ("Test Macro-F1", "Weighted F1", "Accuracy", "Balanced Accuracy"),
        (view.track_c.test_macro_f1, view.track_c.test_weighted_f1, view.track_c.test_accuracy, view.track_c.test_balanced_accuracy),
        strict=True,
    ):
        with column:
            render_metric_card(label, f"{value:.3f}")
    st.caption("Track C metrics describe molecular subtype classification, not survival prediction.")


def render() -> None:
    render_page_intro("Model Evaluation", "Frozen aggregate evaluation evidence from the checksum-verified R9 research boundary.")
    try:
        render_model_evaluation(get_analysis_service())
    except Exception:
        st.error("ARTIFACT_UNAVAILABLE: Frozen aggregate model evaluation metrics are unavailable.")
