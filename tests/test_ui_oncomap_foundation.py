"""R10-B1 visual shell contracts for the visible OncoMap product."""

from __future__ import annotations

from html import unescape
from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]


def _run_app() -> AppTest:
    app = AppTest.from_file(ROOT / "app.py")
    app.run(timeout=30)
    return app


def _visible_text(app: AppTest) -> str:
    element_types = ("title", "header", "subheader", "caption", "markdown", "info", "warning")
    return unescape("\n".join(str(element.value) for kind in element_types for element in app.get(kind)))


def test_oncomap_shell_uses_grouped_judge_facing_navigation() -> None:
    app = _run_app()

    assert not app.exception
    text = _visible_text(app)
    assert "OncoMap" in text
    assert "Breast Cancer Prognosis & Molecular Subtype Analysis" in text
    assert [radio.label for radio in app.sidebar.radio] == ["ONCOMAP", "ANALYSIS", "RESEARCH"]
    assert [radio.options for radio in app.sidebar.radio] == [
        ["Overview"],
        ["Patient Analysis", "Model Evaluation", "Gene Insights"],
        ["Dataset", "Methodology", "About"],
    ]


def test_oncomap_overview_exposes_card_and_workflow_hierarchy() -> None:
    app = _run_app()

    text = _visible_text(app)
    assert "1,904" in text
    assert "68" in text
    assert "2" in text
    assert "6" in text
    assert "Clinical + Genomic Data" in text
    assert any(button.label == "Analyze a Patient →" for button in app.button)
