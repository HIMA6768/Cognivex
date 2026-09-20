"""End-to-end contracts for the R2 biomedical Streamlit shell."""

from __future__ import annotations

import ast
from html import unescape
from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]
APP_TEST_TIMEOUT_SECONDS = 30


def _run_app() -> AppTest:
    app = AppTest.from_file(ROOT / "app.py")
    app.run(timeout=APP_TEST_TIMEOUT_SECONDS)
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


def _navigate(app: AppTest, destination: str) -> None:
    group_index = 0 if destination == "Overview" else 1 if destination in {
        "Patient Analysis", "Model Evaluation", "Gene Insights"
    } else 2
    app.sidebar.radio[group_index].set_value(destination)
    app.run(timeout=APP_TEST_TIMEOUT_SECONDS)


EXPECTED_PAGE_GROUPS = [
    ["Overview"],
    ["Patient Analysis", "Model Evaluation", "Gene Insights"],
    ["Dataset", "Methodology", "About"],
]

DISCLAIMER = (
    "Research and educational prototype only. This application is not a diagnostic medical "
    "device, treatment recommendation system, validated clinical prognosis system, or substitute "
    "for qualified oncology care. Do not use it for patient care."
)


def test_app_starts_with_oncomap_branding_and_approved_navigation() -> None:
    app = _run_app()

    assert not app.exception
    assert [radio.label for radio in app.sidebar.radio] == ["ONCOMAP", "ANALYSIS", "RESEARCH"]
    assert [radio.options for radio in app.sidebar.radio] == EXPECTED_PAGE_GROUPS
    text = _visible_text(app)
    assert "OncoMap" in text
    assert "Breast Cancer Prognosis & Molecular Subtype Analysis" in text
    assert "Research prototype" in text
    assert DISCLAIMER in text


def test_overview_contains_no_dataset_uploader_or_patient_results() -> None:
    app = _run_app()

    assert not app.file_uploader
    assert not app.metric
    assert "OncoMap" in _visible_text(app)
    assert any(button.label == "Analyze a Patient" for button in app.button)


def test_data_cohort_page_shows_validated_aggregates_without_patient_rows() -> None:
    """Replacing aggregate rendering with source rows or an unvalidated state must fail this test."""
    app = _run_app()
    _navigate(app, "Dataset")

    text = _visible_text(app)
    assert not app.exception
    assert "1,904" in text
    assert "Canonical METABRIC artifacts passed integrity and structural validation." in text
    assert "Luminal A" in text
    assert "Version 1" in text
    assert "patient_id" not in text.lower()


def test_data_cohort_page_shows_r3_quality_aggregates_without_patient_rows() -> None:
    """Removing R3 readiness context or exposing source rows would break the Cohort boundary."""
    app = _run_app()
    _navigate(app, "Dataset")

    text = _visible_text(app)
    assert not app.exception
    assert "Data quality" in text
    assert "Clinical missingness" in text
    assert "Survival endpoint" in text
    assert "Genomic data quality" in text
    assert "patient_id" not in text.lower()


def test_data_cohort_page_separates_r3_quality_warnings_from_r4_preprocessing_readiness() -> None:
    """Conflating canonical limitations with R4 readiness would mislead research users."""
    app = _run_app()
    _navigate(app, "Dataset")

    text = _visible_text(app)
    metrics = {metric.label: metric.value for metric in app.metric}
    assert not app.exception
    assert "DATA_QUALITY_READY_WITH_WARNINGS" in text
    assert (metrics["Errors"], metrics["Warnings"], metrics["Information"]) == ("0", "3", "6")
    assert "Preprocessing readiness" in text
    assert "PREPROCESSING_READY" in text
    assert {"Track A", "Track B", "Track C", "Track D"}.issubset(metrics)
    assert (metrics["Track A"], metrics["Track B"], metrics["Track C"], metrics["Track D"]) == (
        "1,903 eligible",
        "1,903 eligible",
        "1,898 eligible",
        "1,903 eligible",
    )
    assert "489" in text
    assert "27" in text
    assert "Clinical + mutation survival preprocessing ready" in text
    assert (
        "The canonical record remains unchanged. R4/R4D exclude it from survival Tracks A/B/D using "
        "NON_POSITIVE_SURVIVAL_DURATION; it remains independently eligible for Track C when Track C requirements pass."
    ) in text
    nc_policy = (
        "Patients labeled as 'NC' (Not Classified) in the raw data are excluded during Track C classification "
        "model training, but are retained for Tracks A, B, and D when their survival eligibility requirements pass."
    )
    assert "NC records: 6" in text
    assert text.count(nc_policy) == 2
    assert "patient_id" not in text.lower()


def test_each_oncomap_page_has_research_context_and_persistent_disclaimer() -> None:
    app = _run_app()
    expected_copy = {
        "Overview": "Analysis workflow",
        "Patient Analysis": "Enter clinical details",
        "Model Evaluation": "Frozen aggregate evaluation evidence",
        "Gene Insights": "Global model-associated coefficients",
        "Dataset": "Validated cohort",
        "Methodology": "Analysis pipeline",
        "About": "Research prototype",
    }

    for destination, expected in expected_copy.items():
        _navigate(app, destination)

        text = _visible_text(app)
        assert not app.exception
        assert expected in text
        assert DISCLAIMER in text


def test_analysis_and_aggregate_pages_expose_r9_functional_surfaces_without_an_exception() -> None:
    app = _run_app()
    expectations = {
        "Patient Analysis": "Step 1: Clinical details",
        "Gene Insights": "Strongest model-associated features",
        "Model Evaluation": "Prognosis evaluation",
    }
    for destination, expected in expectations.items():
        _navigate(app, destination)
        assert not app.exception
        assert expected in _visible_text(app)


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
    assert values["page_title"] == "OncoMap | Breast Cancer Research Analysis"
    assert values["initial_sidebar_state"] == "auto"
