"""Aggregate-only METABRIC Data / Cohort workspace."""

from __future__ import annotations

import streamlit as st

from src.contracts import AnalysisStatus, DataQualitySeverity, DataQualityStatus

from ..components.layout import render_page_header
from ..data_cohort_state import get_metabric_ingestion_state, get_metabric_quality_state


KAGGLE_URL = "https://www.kaggle.com/datasets/raghadalharbi/breast-cancer-gene-expression-profiles-metabric"


def _humanize(field_name: str) -> str:
    return field_name.replace("_", " ").capitalize()


def render() -> None:
    render_page_header(
        "Data / Cohort",
        "Validated aggregate METABRIC cohort information for research use only.",
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
    st.markdown(f"**Validated cohort:** {cohort.patient_records:,} research records")
    summary_columns = st.columns(3)
    summary_columns[0].metric("Matched genomic samples", f"{cohort.matched_samples:,}")
    summary_columns[1].metric("Prepared data columns", f"{metadata.column_count:,}")
    summary_columns[2].metric("Clinical baseline features", f"{metadata.clinical_feature_count:,}")

    st.subheader("Locked patient-level partitions")
    split_summary = cohort.split_summary
    assert split_summary is not None
    split_columns = st.columns(3)
    split_columns[0].metric("Train", f"{split_summary.train_patients:,}")
    split_columns[1].metric("Validation", f"{split_summary.validation_patients:,}")
    split_columns[2].metric("Test", f"{split_summary.test_patients:,}")
    st.caption("The application renders aggregate counts only; no individual records are displayed.")

    st.subheader("Data quality")
    status_messages = {
        DataQualityStatus.DATA_QUALITY_READY: "Data-quality checks are ready for downstream engineering.",
        DataQualityStatus.DATA_QUALITY_READY_WITH_WARNINGS: "Data-quality checks are ready with downstream engineering warnings.",
        DataQualityStatus.DATA_QUALITY_BLOCKED: "Data-quality checks are blocked by structural errors.",
    }
    if quality_report.status is DataQualityStatus.DATA_QUALITY_BLOCKED:
        st.error(status_messages[quality_report.status])
    elif quality_report.status is DataQualityStatus.DATA_QUALITY_READY_WITH_WARNINGS:
        st.warning(status_messages[quality_report.status])
    else:
        st.success(status_messages[quality_report.status])
    quality_columns = st.columns(3)
    quality_columns[0].metric("Errors", quality_report.error_count)
    quality_columns[1].metric("Warnings", quality_report.warning_count)
    quality_columns[2].metric("Information", quality_report.information_count)

    if quality_report.survival is not None:
        survival = quality_report.survival
        st.subheader("Survival endpoint")
        survival_columns = st.columns(3)
        survival_columns[0].metric("Events", f"{survival.event_count:,}")
        survival_columns[1].metric("Censored", f"{survival.censored_count:,}")
        survival_columns[2].metric("Zero durations", f"{survival.zero_time_count:,}")

    if quality_report.clinical_missingness:
        st.subheader("Clinical missingness")
        st.markdown(
            " · ".join(
                f"**{_humanize(summary.field_name)}:** {summary.missing_count:,} missing"
                for summary in quality_report.clinical_missingness
            )
        )

    if quality_report.split_summaries:
        st.subheader("R3 split distribution")
        split_quality_columns = st.columns(3)
        for column, summary in zip(split_quality_columns, quality_report.split_summaries, strict=True):
            column.metric(summary.split.capitalize(), f"{summary.patient_count:,}")
            column.caption(f"{summary.event_count:,} events · {summary.censored_count:,} censored")

    if quality_report.subtype is not None:
        st.subheader("Subtype quality")
        st.markdown(
            " · ".join(
                f"**{count.label}:** {count.count:,}" for count in quality_report.subtype.class_counts
            )
        )
        st.caption(f"NC records: {quality_report.subtype.nc_count:,}. {quality_report.subtype.nc_policy}")

    if quality_report.genomic_summaries:
        st.subheader("Genomic data quality")
        genomic_columns = st.columns(len(quality_report.genomic_summaries))
        for column, summary in zip(genomic_columns, quality_report.genomic_summaries, strict=True):
            column.metric(f"{summary.group_name} features", f"{summary.present_feature_count:,}")
            column.caption(
                f"{summary.missing_value_count:,} missing values · "
                f"{summary.zero_variance_feature_count:,} zero-variance features"
            )

    st.subheader("Actionable data-quality findings")
    for finding in quality_report.findings:
        message = f"**{finding.title}** — {finding.message} {finding.recommendation}"
        if finding.severity is DataQualitySeverity.ERROR:
            st.error(message)
        elif finding.severity is DataQualitySeverity.WARNING:
            st.warning(message)
        else:
            st.info(message)

    st.subheader("Clinical baseline schema")
    st.markdown(
        ", ".join(_humanize(field_name) for field_name in metadata.clinical_feature_names)
    )

    st.subheader("Dataset-confirmed molecular subtype taxonomy")
    st.markdown(", ".join(metadata.subtype_labels))
    st.info(metadata.subtype_nc_policy)

    st.subheader("Active provenance resolution")
    st.markdown(
        f"Kaggle source: [Breast Cancer Gene Expression Profiles (METABRIC)]({KAGGLE_URL}) "
        "by Raghad Alharbi — Version 1. The preserved historical handoff provenance remains "
        "unchanged; the direct verified resolution is documented in `docs/data_provenance_resolution.md`."
    )
