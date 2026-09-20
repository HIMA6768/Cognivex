"""Result-first OncoMap rendering for typed R9/R10-B0 outputs."""

from __future__ import annotations

import streamlit as st

from src.contracts.inference import (
    AnalysisResponse,
    AnalysisTrack,
    FROZEN_SUBTYPE_CLASS_ORDER,
    PrognosisResult,
    SubtypeClassificationResult,
    TrackOutcome,
    TrackReadinessState,
)

from ..navigation import Page, navigate_to
from .charts import render_named_bar_chart
from .oncomap import render_metric_card, render_research_disclaimer


def _outcome_by_track(response: AnalysisResponse, track: AnalysisTrack) -> TrackOutcome | None:
    return next((outcome for outcome in response.outcomes if outcome.track is track), None)


def _render_readiness(outcome: TrackOutcome | None, label: str) -> None:
    if outcome is None:
        return
    if outcome.state is TrackReadinessState.READY:
        return
    assert outcome.error is not None
    fields = f" Missing fields: {', '.join(outcome.error.missing_fields)}." if outcome.error.missing_fields else ""
    st.warning(f"{label}: {outcome.error.message}{fields}")


def render_survival_estimate_unavailable(result: PrognosisResult) -> None:
    """Keep a valid prognosis available when the optional R10-B0 estimate is absent."""
    st.info("Survival estimates are unavailable for this otherwise ready prognosis result. The frozen model log score remains available in Technical details.")
    with st.expander("Technical details"):
        st.metric(result.output_label, f"{result.value:.4f}")
        st.caption(result.interpretation)


def _render_prognosis(result: PrognosisResult, label: str) -> None:
    st.subheader("Estimated survival")
    st.caption(f"Primary result: {label}")
    estimates = result.survival_estimates
    if estimates is None:
        render_survival_estimate_unavailable(result)
        return
    cards = st.columns(3)
    for column, label_text, value in zip(
        cards,
        ("1 year", "3 years", "5 years"),
        (
            estimates.survival_probability_1y,
            estimates.survival_probability_3y,
            estimates.survival_probability_5y,
        ),
        strict=True,
    ):
        with column:
            render_metric_card(label_text, f"{value * 100:.1f}%", "Model-estimated survival")
    st.line_chart(
        {"Months": (12, 36, 60), "Survival probability": (estimates.survival_probability_1y, estimates.survival_probability_3y, estimates.survival_probability_5y)},
        x="Months",
        y="Survival probability",
        width="stretch",
    )
    render_research_disclaimer()
    with st.expander("Technical details"):
        st.metric(result.output_label, f"{result.value:.4f}")
        st.caption(result.interpretation)


def _render_subtype(result: SubtypeClassificationResult) -> None:
    st.subheader("Molecular subtype")
    probability = result.probabilities[result.class_order.index(result.predicted_class)]
    render_metric_card("Predicted subtype", result.predicted_class, f"{probability * 100:.1f}% model probability")
    render_named_bar_chart(
        tuple((label, probability) for label, probability in zip(result.class_order, result.probabilities, strict=True)),
        value_label="Model probability",
    )
    st.caption("Subtype probabilities are displayed in the frozen six-class R9 order.")


def render_patient_results(response: AnalysisResponse) -> None:
    """Render only current in-memory R9 response data; never persist a result history."""
    st.subheader("Step 5: Results")
    for error in response.request_errors:
        st.error(f"{error.code}: {error.message}")
    track_a = _outcome_by_track(response, AnalysisTrack.TRACK_A)
    track_b = _outcome_by_track(response, AnalysisTrack.TRACK_B)
    track_c = _outcome_by_track(response, AnalysisTrack.TRACK_C)
    primary = track_b if track_b and track_b.state is TrackReadinessState.READY else track_a
    if primary and isinstance(primary.result, PrognosisResult):
        label = "Clinical + genomic prognosis" if primary.track is AnalysisTrack.TRACK_B else "Clinical-only prognosis"
        _render_prognosis(primary.result, label)
        if primary.track is AnalysisTrack.TRACK_B and track_a and track_a.state is TrackReadinessState.READY:
            st.caption("A clinical-only research-model result is also available in Technical details; this is not a patient-specific model comparison.")
    else:
        _render_readiness(track_b, "Clinical + genomic prognosis")
        _render_readiness(track_a, "Clinical-only prognosis")

    if track_c and track_c.state is TrackReadinessState.READY and isinstance(track_c.result, SubtypeClassificationResult):
        if track_c.result.class_order != FROZEN_SUBTYPE_CLASS_ORDER:
            st.error("INFERENCE_ERROR: Frozen subtype class order is unavailable.")
        else:
            _render_subtype(track_c.result)
    else:
        _render_readiness(track_c, "Molecular subtype")

    st.subheader("Global genomic insights")
    st.caption("Genomic associations are global R8 model results and are not patient-specific attributions.")
    st.button("Explore global Gene Insights", on_click=navigate_to, args=(Page.GENE_INSIGHTS,))
