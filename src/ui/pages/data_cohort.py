"""Aggregate-only METABRIC Data / Cohort workspace."""

from __future__ import annotations

import streamlit as st

from src.contracts import (
    AnalysisStatus,
    DataQualitySeverity,
    DataQualityStatus,
    EligibilityReasonCode,
    PreprocessingTask,
)

from ..components.oncomap import render_metric_card, render_page_intro, render_workflow_steps
from ..data_cohort_state import (
    get_metabric_ingestion_state,
    get_metabric_preprocessing_state,
    get_metabric_quality_state,
)


KAGGLE_URL = "https://www.kaggle.com/datasets/raghadalharbi/breast-cancer-gene-expression-profiles-metabric"
NC_SURVIVAL_POLICY = (
    "Patients labeled as 'NC' (Not Classified) in the raw data are excluded during Track C classification "
    "model training, but are retained for Tracks A, B, and D when their survival eligibility requirements pass."
)


def _humanize(field_name: str) -> str:
    return field_name.replace("_", " ").capitalize()


def _exclusion_count(metadata, reason: EligibilityReasonCode) -> int:
    return next((item.count for item in metadata.exclusion_counts if item.reason is reason), 0)


def render() -> None:
    render_page_intro(
        "Dataset",
        "METABRIC cohort overview: 1,904 prepared patients, 693 prepared columns, and a locked 1,332 / 286 / 286 split.",
    )
    refreshed = st.button("Refresh validated data", help="Reload repository-owned canonical artifacts.")
    result = get_metabric_ingestion_state(st.session_state, refresh=refreshed)

    if result.validation.status is not AnalysisStatus.DATA_READY or result.metadata is None:
        st.error(result.validation.message)
        for issue in result.validation.issues:
            st.info(issue.message)
        return

    cohort = result.cohort
    metadata = result.metadata
    quality_report = get_metabric_quality_state(st.session_state, result, refresh=refreshed)
    st.success(result.validation.message)
    summary_columns = st.columns(4)
    for column, label, value, detail in zip(
        summary_columns,
        ("METABRIC patients", "Prepared columns", "Genomic model inputs", "Clinical model inputs"),
        (f"{cohort.patient_records:,}", f"{metadata.column_count:,}", "68", "7"),
        ("Prepared research cohort", "Canonical application dataset", "50 expression + 18 mutation", "Frozen Track A clinical contract"),
        strict=True,
    ):
        with column:
            render_metric_card(label, value, detail)
    st.caption("68 genomic model inputs (50 expression + 18 mutation) · 7 clinical model inputs")

    st.subheader("Locked data split")
    split_summary = cohort.split_summary
    assert split_summary is not None
    split_columns = st.columns(3)
    split_columns[0].metric("Train", f"{split_summary.train_patients:,}")
    split_columns[1].metric("Validation", f"{split_summary.validation_patients:,}")
    split_columns[2].metric("Test", f"{split_summary.test_patients:,}")
    st.bar_chart(
        {"Patients": {"Train": split_summary.train_patients, "Validation": split_summary.validation_patients, "Test": split_summary.test_patients}},
        horizontal=True,
        width="stretch",
    )
    st.caption("The split is locked and used consistently. OncoMap renders aggregate cohort information only.")

    if quality_report.survival is not None:
        survival = quality_report.survival
        st.subheader("Survival endpoint")
        survival_columns = st.columns(3)
        for column, label, value in zip(
            survival_columns,
            ("Events", "Censored", "Zero-duration record"),
            (survival.event_count, survival.censored_count, survival.zero_time_count),
            strict=True,
        ):
            with column:
                render_metric_card(label, f"{value:,}")

    if quality_report.subtype is not None:
        subtype = quality_report.subtype
        counts = {item.label: item.count for item in subtype.class_counts}
        st.subheader("Molecular subtype distribution")
        subtype_order = ("Luminal A", "Luminal B", "Her2", "Basal", "Claudin-low", "Normal-like")
        st.bar_chart(
            {"Patients": {label: counts.get(label, 0) for label in subtype_order}},
            horizontal=True,
            width="stretch",
        )
        st.caption(f"NC excluded from Track C: {subtype.nc_count:,}. {NC_SURVIVAL_POLICY}")

    st.subheader("Data quality at a glance")
    status_messages = {
        DataQualityStatus.DATA_QUALITY_READY: "DATA_QUALITY_READY — Data-quality checks are ready for downstream engineering.",
        DataQualityStatus.DATA_QUALITY_READY_WITH_WARNINGS: (
            "DATA_QUALITY_READY_WITH_WARNINGS — The canonical source data contains known limitations "
            "that downstream engineering must handle."
        ),
        DataQualityStatus.DATA_QUALITY_BLOCKED: "DATA_QUALITY_BLOCKED — Data-quality checks are blocked by structural errors.",
    }
    if quality_report.status is DataQualityStatus.DATA_QUALITY_BLOCKED:
        st.error(status_messages[quality_report.status])
    elif quality_report.status is DataQualityStatus.DATA_QUALITY_READY_WITH_WARNINGS:
        st.warning(status_messages[quality_report.status])
    else:
        st.success(status_messages[quality_report.status])
    quality_columns = st.columns(4)
    missingness = {summary.field_name: summary.missing_count for summary in quality_report.clinical_missingness}
    unknown_stage = next(
        (finding.affected_count for finding in quality_report.findings if finding.code == "TUMOR_STAGE_UNKNOWN"),
        0,
    )
    for column, label, value in zip(
        quality_columns,
        ("Structural errors", "Known warnings", "Tumor size missing", "ER-IHC missing"),
        (quality_report.error_count, quality_report.warning_count, missingness.get("tumor_size", 0), missingness.get("er_status_measured_by_ihc", 0)),
        strict=True,
    ):
        with column:
            render_metric_card(label, f"{value:,}")
    st.caption(
        f"Unknown tumor stage: {unknown_stage:,}. Zero survival duration: "
        f"{quality_report.survival.zero_time_count if quality_report.survival else 0:,}. "
        "Known data limitations remain visible for transparency."
    )

    st.subheader("Current OncoMap model inputs")
    input_columns = st.columns(3)
    for column, track, detail in zip(
        input_columns,
        ("Track A", "Track B", "Track C"),
        ("7 clinical", "7 clinical + 50 expression + 18 mutation", "50 expression + 18 mutation"),
        strict=True,
    ):
        with column:
            render_metric_card(track, detail)

    st.subheader("METABRIC provenance")
    st.caption(
        f"[Breast Cancer Gene Expression Profiles (METABRIC)]({KAGGLE_URL}) by Raghad Alharbi, Version 1. "
        "The repository uses a prepared, checksum-validated METABRIC cohort with a locked split."
    )

    with st.expander("View technical cohort details"):
        preprocessing_report = get_metabric_preprocessing_state(st.session_state, refresh=refreshed)
        preprocessing_by_task = {item.task: item for item in preprocessing_report.tasks}
        track_a = preprocessing_by_task[PreprocessingTask.CLINICAL_SURVIVAL]
        track_b = preprocessing_by_task[PreprocessingTask.CLINICAL_MRNA_SURVIVAL]
        track_c = preprocessing_by_task[PreprocessingTask.SUBTYPE_CLASSIFICATION]
        track_d = preprocessing_by_task[PreprocessingTask.CLINICAL_MUTATION_SURVIVAL]
        assert track_d.mutation_metadata is not None
        st.markdown(
            "**R3/R4/R4D engineering evidence** — aggregate-only quality validation and leak-safe, "
            "training-only preprocessing remain available for historical review."
        )
        render_workflow_steps(("R3 quality", "R4 preprocessing", "R4D mutation preparation", "Frozen models"))
        st.markdown(
            " · ".join(
                (
                    f"**489 mRNA features:** {len(track_b.mrna_feature_names):,}",
                    f"**173 mutation features:** {len(track_d.mutation_metadata.source_feature_names):,}",
                    f"**Track D retained mutation features:** {len(track_d.mutation_metadata.selection.retained_feature_names):,}",
                    f"**Forbidden predictor leakage:** {preprocessing_report.forbidden_feature_count:,}",
                    f"**NC Track C exclusions:** {_exclusion_count(track_c, EligibilityReasonCode.NC_SUBTYPE):,}",
                    f"**Zero-duration survival exclusions:** {_exclusion_count(track_a, EligibilityReasonCode.NON_POSITIVE_SURVIVAL_DURATION):,}",
                )
            )
        )
        st.caption("Track D is historical preprocessing evidence; it is not a current OncoMap prediction architecture.")
        st.markdown("**Full missingness:** " + " · ".join(
            f"{_humanize(summary.field_name)} {summary.missing_count:,}"
            for summary in quality_report.clinical_missingness
        ))
        st.markdown("**Split event/censor detail:** " + " · ".join(
            f"{summary.split.capitalize()} {summary.event_count:,} events / {summary.censored_count:,} censored"
            for summary in quality_report.split_summaries
        ))
