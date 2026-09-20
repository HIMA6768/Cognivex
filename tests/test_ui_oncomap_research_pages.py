"""Judge-facing OncoMap research-page rendering contracts."""

from __future__ import annotations

from html import unescape
from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]


def _app() -> AppTest:
    app = AppTest.from_file(ROOT / "app.py")
    app.run(timeout=30)
    return app


def _text(app: AppTest) -> str:
    return unescape(
        "\n".join(
            str(element.value)
            for kind in ("title", "header", "subheader", "caption", "markdown", "info", "warning", "error")
            for element in app.get(kind)
        )
    )


def test_overview_explains_system_facts_workflow_and_patient_cta() -> None:
    app = _app()

    text = _text(app)
    assert not app.exception
    assert "OncoMap" in text
    assert "1,904" in text
    assert "68" in text
    assert "2" in text
    assert "6" in text
    assert "Clinical + Genomic Data" in text
    assert any(button.label == "Analyze a Patient" for button in app.button)


def test_model_evaluation_and_gene_insights_use_frozen_aggregate_views() -> None:
    app = _app()
    app.sidebar.radio[1].set_value("Model Evaluation")
    app.run(timeout=30)

    text = _text(app)
    assert not app.exception
    assert "0.651" in text
    assert "0.641" in text
    assert "Overall evidence is mixed" in text
    assert "Test Macro-F1" in text

    app.sidebar.radio[1].set_value("Gene Insights")
    app.run(timeout=30)
    text = _text(app)
    assert not app.exception
    assert "68" in text and "Analyzed" in text
    assert "24" in text and "Active" in text
    assert "44" in text and "Near-zero" in text
    assert any(expander.label == "View all genomic features" for expander in app.expander)
    assert "not causal findings" in text


def test_dataset_methodology_and_about_are_aggregate_research_pages() -> None:
    app = _app()
    app.sidebar.radio[2].set_value("Dataset")
    app.run(timeout=30)
    dataset_text = _text(app)
    assert not app.exception
    assert "METABRIC" in dataset_text
    assert "1,332" in dataset_text
    assert "patient_id" not in dataset_text.lower()

    app.sidebar.radio[2].set_value("Methodology")
    app.run(timeout=30)
    assert "Analysis pipeline" in _text(app)

    app.sidebar.radio[2].set_value("About")
    app.run(timeout=30)
    assert "Research prototype" in _text(app)
