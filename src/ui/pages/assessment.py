"""P4 vehicle-image upload, structural validation, and preview page."""

from __future__ import annotations

import streamlit as st

from src.config.settings import AppSettings

from ..components.layout import render_page_header
from ..quality_gate import QualityReport, QualityThresholds, evaluate_quality
from ..upload_flow import (
    ANALYSIS_REQUESTED_KEY,
    ImageValidationLimits,
    RESET_UPLOAD_REQUESTED_KEY,
    UPLOAD_STATE_KEY,
    reset_upload,
    selected_upload,
    store_upload,
    validate_image_upload,
)


def _request_reset() -> None:
    """Defer widget-state clearing until before the next uploader render."""
    st.session_state[RESET_UPLOAD_REQUESTED_KEY] = True
    st.rerun()


def _render_upload_guidance(max_upload_mb: int) -> None:
    """Render concise, accessible preparation guidance before selection."""
    left, right = st.columns(2)
    with left:
        st.markdown("**Supported formats**  \nJPG / JPEG / PNG / WEBP")
        st.markdown(f"**Maximum upload: {max_upload_mb} MB**")
    with right:
        st.markdown("**Photo tips**")
        st.markdown(
            "- ensure the damaged area is visible\n"
            "- avoid severe blur\n"
            "- use adequate lighting\n"
            "- include sufficient vehicle context"
        )


def _render_ready_upload(quality_report: QualityReport) -> None:
    """Render the selected-image preview and the safe P4 analysis boundary."""
    image = selected_upload(st.session_state)
    if image is None:
        return

    with st.container(border=True):
        st.subheader("Image ready for analysis")
        st.image(image.preview_data, caption=image.name, width="stretch")
        st.caption("The image is stored only for this Streamlit session.")
        if not quality_report.passed:
            st.warning("Improve the image quality below before starting an assessment.")
            for check in quality_report.checks:
                if not check.passed and check.message is not None:
                    st.error(check.message)
        action_column, reset_column = st.columns((1, 1))
        with action_column:
            if st.button(
                "Analyze damage",
                type="primary",
                disabled=not quality_report.passed,
                key="analyze_damage",
            ):
                st.session_state[ANALYSIS_REQUESTED_KEY] = True
        with reset_column:
            if st.button("Upload another image", key="reset_assessment_upload"):
                _request_reset()

    if quality_report.passed and st.session_state.get(ANALYSIS_REQUESTED_KEY):
        st.info(
            "Image passed structural and quality checks. AI analysis is not available yet. "
            "No prediction is shown."
        )


def render() -> None:
    """Render the P4 upload workflow without invoking assessment logic."""
    if st.session_state.pop(RESET_UPLOAD_REQUESTED_KEY, False):
        reset_upload(st.session_state)

    settings = AppSettings.from_env()
    limits = ImageValidationLimits(
        min_width=settings.thresholds.min_image_width,
        min_height=settings.thresholds.min_image_height,
        max_width=settings.thresholds.max_image_width,
        max_height=settings.thresholds.max_image_height,
        max_pixels=settings.thresholds.max_image_pixels,
    )
    render_page_header(
        "Vehicle Damage Assessment",
        "Upload a clear photo of the damaged vehicle for an AI-assisted preliminary assessment.",
    )
    _render_upload_guidance(settings.upload.max_upload_mb)
    uploaded_file = st.file_uploader(
        "Upload a vehicle image",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=False,
        key="assessment_file_input",
        help="Drag and drop a supported vehicle image, or browse for a file.",
    )

    if uploaded_file is not None:
        result = validate_image_upload(
            uploaded_file.name,
            uploaded_file.type,
            uploaded_file.getvalue(),
            settings.upload.max_upload_bytes,
            limits,
        )
        if result.failure is not None:
            st.session_state.pop(ANALYSIS_REQUESTED_KEY, None)
            st.session_state.pop(UPLOAD_STATE_KEY, None)
            st.error(result.failure.message)
            if st.button("Upload another image", key="reset_invalid_assessment_upload"):
                _request_reset()
            return
        if result.image is not None:
            store_upload(st.session_state, result.image)

    if selected_upload(st.session_state) is None:
        st.info("Select a supported vehicle image to review it before analysis.")
        st.button("Analyze damage", type="primary", disabled=True, key="analyze_damage")
        return

    image = selected_upload(st.session_state)
    assert image is not None
    quality_report = evaluate_quality(
        image,
        QualityThresholds(
            min_laplacian_variance=settings.thresholds.min_laplacian_variance,
            min_mean_luminance=settings.thresholds.min_mean_luminance,
            max_mean_luminance=settings.thresholds.max_mean_luminance,
            min_tile_laplacian_variance=settings.thresholds.min_tile_laplacian_variance,
            min_usable_sharp_tile_ratio=settings.thresholds.min_usable_sharp_tile_ratio,
            min_median_luminance=settings.thresholds.min_median_luminance,
            dark_pixel_luminance=settings.thresholds.dark_pixel_luminance,
            max_dark_pixel_ratio=settings.thresholds.max_dark_pixel_ratio,
            max_median_luminance=settings.thresholds.max_median_luminance,
            bright_pixel_luminance=settings.thresholds.bright_pixel_luminance,
            max_bright_pixel_ratio=settings.thresholds.max_bright_pixel_ratio,
        ),
    )
    if not quality_report.passed:
        st.session_state.pop(ANALYSIS_REQUESTED_KEY, None)
    _render_ready_upload(quality_report)
