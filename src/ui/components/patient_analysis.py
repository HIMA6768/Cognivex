"""Transient, structured patient-analysis input flow over the public R9 service."""

from __future__ import annotations

from collections.abc import Mapping

import streamlit as st

from src.contracts.inference import AnalysisRequest, AnalysisTrack


_STAGE_KEY = "oncomap_patient_stage"
_RESPONSE_KEY = "oncomap_patient_response"
_DRAFT_KEY = "oncomap_patient_draft"
_INPUT_PREFIX = "oncomap_patient_input_"
_CLINICAL_NUMERIC = ("age_at_diagnosis", "tumor_size", "lymph_nodes_examined_positive")
_CLINICAL_CATEGORICAL = (
    "tumor_stage",
    "er_status_measured_by_ihc",
    "pr_status",
    "her2_status",
)
_STAGE_LABELS = ("Clinical", "Genomic", "Review", "Run", "Results")


def build_patient_request(values: Mapping[str, str | int | float | None]) -> AnalysisRequest:
    """Create one exact R9 request without UI-side feature validation or derivation."""
    return AnalysisRequest(dict(values), (AnalysisTrack.TRACK_A, AnalysisTrack.TRACK_B, AnalysisTrack.TRACK_C))


def synthetic_demo_profile(
    clinical_fields: tuple[str, ...],
    expression_fields: tuple[str, ...],
    mutation_fields: tuple[str, ...],
) -> dict[str, str | float]:
    """Return a labelled non-patient profile using only the frozen raw field contract."""
    clinical = {
        "age_at_diagnosis": 55.0,
        "tumor_size": 2.4,
        "tumor_stage": "2",
        "lymph_nodes_examined_positive": 1.0,
        "er_status_measured_by_ihc": "Positive",
        "pr_status": "Positive",
        "her2_status": "Negative",
    }
    if tuple(clinical) != clinical_fields or len(expression_fields) != 50 or len(mutation_fields) != 18:
        raise ValueError("frozen patient-analysis contract is unavailable")
    return {**clinical, **{field: 0.0 for field in expression_fields}, **{field: "0" for field in mutation_fields}}


def _input_key(field: str) -> str:
    return f"{_INPUT_PREFIX}{field}"


def _set_stage(stage: int) -> None:
    st.session_state[_STAGE_KEY] = stage


def _load_demo(profile: Mapping[str, str | float]) -> None:
    for field, value in profile.items():
        st.session_state[_input_key(field)] = value
    st.session_state[_DRAFT_KEY] = dict(profile)
    st.session_state.pop(_RESPONSE_KEY, None)
    _set_stage(1)


def render_patient_steps(stage: int) -> None:
    """Render the five visible flow stages without model terminology."""
    columns = st.columns(len(_STAGE_LABELS))
    for number, (column, label) in enumerate(zip(columns, _STAGE_LABELS, strict=True), start=1):
        with column:
            prefix = "●" if number == stage else "○"
            st.caption(f"{prefix} {number}. {label}")


def _provided_value(field: str) -> str | float | None:
    value = st.session_state.get(_input_key(field))
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, (float, int)) and not isinstance(value, bool):
        return float(value)
    return None


def collect_patient_values(fields: tuple[str, ...]) -> dict[str, str | float | None]:
    """Collect only transient widget values that the user actually supplied."""
    draft = dict(st.session_state.get(_DRAFT_KEY, {}))
    for field in fields:
        if (value := _provided_value(field)) is not None:
            draft[field] = value
    return {field: draft[field] for field in fields if field in draft and draft[field] is not None}


def _save_and_advance(fields: tuple[str, ...], stage: int) -> None:
    """Snapshot transient widget state before Streamlit removes hidden step widgets."""
    draft = dict(st.session_state.get(_DRAFT_KEY, {}))
    draft.update(collect_patient_values(fields))
    st.session_state[_DRAFT_KEY] = draft
    _set_stage(stage)


def _clinical_input(clinical_fields: tuple[str, ...]) -> None:
    labels = {
        "age_at_diagnosis": "Age at diagnosis (years)",
        "tumor_size": "Tumor size (cm)",
        "tumor_stage": "Tumor stage",
        "lymph_nodes_examined_positive": "Positive lymph nodes",
        "er_status_measured_by_ihc": "ER status",
        "pr_status": "PR status",
        "her2_status": "HER2 status",
    }
    left, right = st.columns(2)
    for index, field in enumerate(clinical_fields):
        with (left if index % 2 == 0 else right):
            label = labels[field]
            if field in _CLINICAL_NUMERIC:
                st.number_input(label, value=None, step=0.1, key=_input_key(field))
            elif field == "tumor_stage":
                st.selectbox(label, (None, "1", "2", "3", "4", "Unknown"), key=_input_key(field))
            else:
                st.selectbox(label, (None, "Negative", "Positive", "Unknown"), key=_input_key(field))


def _genomic_input(expression_fields: tuple[str, ...], mutation_fields: tuple[str, ...]) -> None:
    st.caption("Advanced profile: enter only values you have. R9 reports readiness for incomplete input without the UI deriving any model features.")
    expression_tab, mutation_tab = st.tabs(("Gene expression (50)", "Mutation annotations (18)"))
    with expression_tab:
        columns = st.columns(2)
        for index, field in enumerate(expression_fields):
            with columns[index % 2]:
                st.number_input(field, value=None, step=0.01, format="%.4f", key=_input_key(field))
    with mutation_tab:
        columns = st.columns(2)
        for index, field in enumerate(mutation_fields):
            with columns[index % 2]:
                st.text_input(field, key=_input_key(field), placeholder="0 or mutation annotation")


def render_patient_analysis(service) -> None:
    """Render the transient five-step input journey and invoke only public R9 analysis."""
    clinical_fields = service.registry.track_a.required_fields
    genomic_fields = service.registry.track_c.required_fields
    expression_fields, mutation_fields = genomic_fields[:50], genomic_fields[50:]
    if len(clinical_fields) != 7 or len(expression_fields) != 50 or len(mutation_fields) != 18:
        st.error("ARTIFACT_UNAVAILABLE: Frozen input contracts are unavailable.")
        return
    all_fields = clinical_fields + genomic_fields
    stage = int(st.session_state.get(_STAGE_KEY, 1))
    stage = min(max(stage, 1), 5)
    st.session_state[_STAGE_KEY] = stage
    render_patient_steps(stage)
    st.button(
        "Load synthetic demo profile — not patient data",
        on_click=_load_demo,
        args=(synthetic_demo_profile(clinical_fields, expression_fields, mutation_fields),),
    )

    if stage == 1:
        st.subheader("Step 1: Clinical details")
        st.caption("These seven inputs support the prognosis models. Fields left blank remain partial input for R9 readiness handling.")
        _clinical_input(clinical_fields)
        st.button("Save and continue", type="primary", on_click=_save_and_advance, args=(clinical_fields, 2))
        return
    if stage == 2:
        st.subheader("Step 2: Genomic profile")
        _genomic_input(expression_fields, mutation_fields)
        previous, next_step = st.columns(2)
        previous.button("Back", on_click=_set_stage, args=(1,))
        next_step.button("Save and continue", type="primary", on_click=_save_and_advance, args=(genomic_fields, 3))
        return

    values = collect_patient_values(all_fields)
    clinical_count = sum(field in values for field in clinical_fields)
    expression_count = sum(field in values for field in expression_fields)
    mutation_count = sum(field in values for field in mutation_fields)
    if stage == 3:
        st.subheader("Step 3: Review / validate")
        review = st.columns(3)
        review[0].metric("Clinical fields", f"{clinical_count}/7")
        review[1].metric("Expression fields", f"{expression_count}/50")
        review[2].metric("Mutation fields", f"{mutation_count}/18")
        st.caption("The service, not the UI, determines readiness and validation from the exact frozen R9 contract.")
        previous, next_step = st.columns(2)
        previous.button("Back", on_click=_set_stage, args=(2,))
        next_step.button("Continue to run", type="primary", on_click=_set_stage, args=(4,))
        return
    if stage == 4:
        st.subheader("Step 4: Run analysis")
        st.caption("Run the available research analyses once using the current transient form values.")
        previous, run = st.columns(2)
        previous.button("Back", on_click=_set_stage, args=(3,))
        if run.button("Run analysis", type="primary"):
            st.session_state[_RESPONSE_KEY] = service.analyze(build_patient_request(values))
            _set_stage(5)
            st.rerun()
        return
