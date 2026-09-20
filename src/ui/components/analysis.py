"""Safe Streamlit rendering helpers for frozen R9 contract results."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd
import streamlit as st

from src.contracts.inference import (
    AnalysisRequest, AnalysisResponse, AnalysisTrack, PrognosticFeatureAnalysisOutcome, RequestError, SubtypeClassificationResult,
    TrackOutcome, TrackReadinessState,
)
from src.services.analysis import AnalysisService


def track_label(track: AnalysisTrack) -> str:
    return {AnalysisTrack.TRACK_A: "Track A", AnalysisTrack.TRACK_B: "Track B", AnalysisTrack.TRACK_C: "Track C"}[track]


def parse_contract_lines(
    text: str, *, allowed_fields: tuple[str, ...], numeric_fields: tuple[str, ...], nullable_fields: tuple[str, ...],
) -> dict[str, str | float | None]:
    """Parse optional exact-contract `field=value` lines without retaining input."""
    parsed: dict[str, str | float | None] = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        name, separator, raw = line.partition("=")
        name, raw = name.strip(), raw.strip()
        if not separator:
            parsed[name] = raw
        else:
            parsed[name] = parse_contract_value(name, raw, numeric_fields=numeric_fields, nullable_fields=nullable_fields)
    return parsed


def parse_contract_value(
    name: str, raw: str, *, numeric_fields: tuple[str, ...], nullable_fields: tuple[str, ...],
) -> str | float | None:
    """Convert only presentation-level numeric/null syntax; R9 retains validation authority."""
    if raw.lower() == "null" and name in nullable_fields:
        return None
    if name in numeric_fields:
        try:
            return float(raw)
        except ValueError:
            return raw
    return raw


def render_request_errors(errors: Iterable[RequestError]) -> None:
    for error in errors:
        fields = f" Fields: {', '.join(error.fields)}." if error.fields else ""
        st.error(f"{error.code}: {error.message}{fields}")


def submit_track_request(
    service: AnalysisService, track: AnalysisTrack, values: dict[str, str | float | None],
) -> AnalysisResponse:
    """Create the exact R9 request boundary; no UI-side validation or inference occurs."""
    return service.analyze(AnalysisRequest(values, (track,)))


def render_track_outcome(outcome: TrackOutcome) -> None:
    """Render only typed R9 results or safe error/messages; never request values."""
    prefix = track_label(outcome.track)
    if outcome.state is not TrackReadinessState.READY:
        assert outcome.error is not None
        missing = f" Missing fields: {', '.join(outcome.error.missing_fields)}." if outcome.error.missing_fields else ""
        renderer = st.warning if outcome.state is TrackReadinessState.MISSING_REQUIRED_FIELDS else st.error
        renderer(f"{prefix}: {outcome.error.message}{missing}")
        return
    assert outcome.result is not None
    if isinstance(outcome.result, SubtypeClassificationResult):
        st.subheader(f"{prefix} molecular subtype result")
        st.markdown(f"**Predicted molecular subtype:** {outcome.result.predicted_class}")
        st.dataframe(
            pd.DataFrame({"Subtype": outcome.result.class_order, "Probability": outcome.result.probabilities}),
            hide_index=True,
            use_container_width=True,
        )
        return
    st.metric(outcome.result.output_label, f"{outcome.result.value:.4f}")
    st.caption(outcome.result.interpretation)


def render_r8_analysis(outcome: PrognosticFeatureAnalysisOutcome) -> None:
    """Render R8's global coefficient table only, never a patient attribution."""
    if outcome.error is not None:
        st.error(f"{outcome.error.code}: {outcome.error.message}")
        return
    assert outcome.view is not None
    st.caption(outcome.view.interpretation)
    st.dataframe(
        pd.DataFrame(
            {
                "Rank": [item.effect.rank for item in outcome.view.effects],
                "Feature": [item.effect.raw_feature_name for item in outcome.view.effects],
                "Type": [item.effect.feature_type.value for item in outcome.view.effects],
                "Model coefficient": [item.effect.beta for item in outcome.view.effects],
                "Direction": [item.effect.direction_display for item in outcome.view.effects],
                "Active": [item.effect.is_active for item in outcome.view.effects],
            }
        ),
        hide_index=True,
        use_container_width=True,
    )


def render_clinical_inputs(
    fields: tuple[str, ...], *, key_prefix: str, numeric_fields: tuple[str, ...], nullable_fields: tuple[str, ...],
) -> dict[str, str | float | None]:
    """Collect an optional partial clinical mapping using exact supplied contract fields."""
    values: dict[str, str | float | None] = {}
    for field in fields:
        raw = st.text_input(field.replace("_", " ").capitalize(), key=f"{key_prefix}_{field}")
        if raw.strip():
            values[field] = parse_contract_value(field, raw.strip(), numeric_fields=numeric_fields, nullable_fields=nullable_fields)
    return values


def render_genomic_input(
    fields: tuple[str, ...], *, key_prefix: str, numeric_fields: tuple[str, ...], nullable_fields: tuple[str, ...] = (),
) -> dict[str, str | float | None]:
    """Collect optional exact `field=value` genomic input with no feature discovery."""
    st.caption(f"Use one `field=value` line for any of the {len(fields)} frozen genomic fields. Leave lines absent for partial readiness.")
    raw = st.text_area("Genomic fields", key=f"{key_prefix}_genomic_fields", height=220)
    return parse_contract_lines(raw, allowed_fields=fields, numeric_fields=numeric_fields, nullable_fields=nullable_fields)
