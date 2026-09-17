"""Aggregate-only METABRIC Data / Cohort workspace."""

from __future__ import annotations

import streamlit as st

from src.contracts import AnalysisStatus

from ..components.layout import render_page_header
from ..data_cohort_state import get_metabric_ingestion_state


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
