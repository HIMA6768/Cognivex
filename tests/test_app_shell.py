"""End-to-end contracts for the R2 biomedical Streamlit shell."""

from __future__ import annotations

import ast
from html import unescape
from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]


def _run_app() -> AppTest:
    app = AppTest.from_file(ROOT / "app.py")
    app.run()
    return app


def _visible_text(app: AppTest) -> str:
    element_types = (
        "title",
        "header",
        "subheader",
        "caption",
        "markdown",
        "info",
        "success",
        "warning",
        "error",
    )
    return unescape(
        "\n".join(
            str(element.value)
            for element_type in element_types
            for element in app.get(element_type)
        )
    )


EXPECTED_PAGES = [
    "Overview",
    "Data / Cohort",
    "Survival Analysis",
    "Subtype Classification",
    "Gene Insights",
    "Model Comparison",
    "Methodology / About",
]

DISCLAIMER = (
    "Research and educational prototype only. This application is not a diagnostic medical "
    "device, treatment recommendation system, validated clinical prognosis system, or substitute "
    "for qualified oncology care. Do not use it for patient care."
)


def test_app_starts_with_biomedical_branding_and_approved_navigation() -> None:
    app = _run_app()

    assert not app.exception
    assert app.sidebar.radio[0].label == "Navigation"
    assert app.sidebar.radio[0].options == EXPECTED_PAGES
    text = _visible_text(app)
    assert "Breast Cancer Prognosis & Subtype Classification" in text
    assert "Clinical and genomic research analytics" in text
    assert "Research prototype" in text
    assert DISCLAIMER in text


def test_overview_contains_no_dataset_uploader_metrics_or_patient_results() -> None:
    app = _run_app()

    assert not app.file_uploader
    assert not app.metric
    assert "Canonical cohort data is available" in _visible_text(app)


def test_data_cohort_page_shows_validated_aggregates_without_patient_rows() -> None:
    """Replacing aggregate rendering with source rows or an unvalidated state must fail this test."""
    app = _run_app()
    app.sidebar.radio[0].set_value("Data / Cohort")
    app.run()

    text = _visible_text(app)
    assert not app.exception
    assert "1,904" in text
    assert "Canonical METABRIC artifacts passed integrity and structural validation." in text
    assert "Luminal A" in text
    assert "Version 1" in text
    assert "patient_id" not in text.lower()


def test_each_page_has_an_honest_pending_state_and_persistent_disclaimer() -> None:
    app = _run_app()
    expected_copy = {
        "Overview": "Canonical cohort data is available",
        "Data / Cohort": "Validated cohort",
        "Survival Analysis": "Survival analysis is pending validated cohort data and model handoff",
        "Subtype Classification": "Subtype classification is pending gene-expression data and confirmed dataset labels",
        "Gene Insights": "Gene-level insights are pending evaluated model outputs",
        "Model Comparison": "Evaluation pending model handoff",
        "Methodology / About": "Clinical-only versus clinical-plus-genomic prognosis",
    }

    for destination, pending_copy in expected_copy.items():
        app.sidebar.radio[0].set_value(destination)
        app.run()

        text = _visible_text(app)
        assert not app.exception
        assert pending_copy in text
        assert DISCLAIMER in text


def test_subtype_page_does_not_freeze_or_invent_a_taxonomy() -> None:
    app = _run_app()
    app.sidebar.radio[0].set_value("Subtype Classification")
    app.run()

    text = _visible_text(app)
    assert "Exact subtype labels will be taken from the selected dataset after handoff." in text
    for unverified_label in ("Luminal A", "Luminal B", "HER2-enriched", "Basal-like"):
        assert unverified_label not in text


def test_page_renderer_registry_covers_every_navigation_destination() -> None:
    from src.ui.navigation import PAGE_ORDER
    from src.ui.shell import PAGE_RENDERERS

    assert tuple(PAGE_RENDERERS) == PAGE_ORDER


def test_page_configuration_precedes_rendering_and_uses_biomedical_metadata() -> None:
    tree = ast.parse((ROOT / "app.py").read_text())
    calls = [
        statement.value
        for statement in tree.body
        if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call)
    ]
    page_config_call = next(
        call
        for call in calls
        if isinstance(call.func, ast.Attribute) and call.func.attr == "set_page_config"
    )
    render_app_call = next(
        call
        for call in calls
        if isinstance(call.func, ast.Name) and call.func.id == "render_app"
    )
    values = {
        keyword.arg: keyword.value.value
        for keyword in page_config_call.keywords
        if isinstance(keyword.value, ast.Constant)
    }

    assert calls.index(page_config_call) < calls.index(render_app_call)
    assert values["page_title"] == "Breast Cancer Prognosis & Subtype Classification"
    assert values["initial_sidebar_state"] == "auto"
