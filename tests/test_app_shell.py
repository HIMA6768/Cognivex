"""End-to-end contracts for the pre-model Streamlit application shell."""

from __future__ import annotations

import ast
from io import BytesIO
from pathlib import Path

from PIL import Image
from streamlit.testing.v1 import AppTest


def _run_app() -> AppTest:
    """Run the public entrypoint in Streamlit's test runtime."""
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py")
    app.run()
    return app


def _visible_text(app: AppTest) -> str:
    """Collect text exposed by Streamlit elements, excluding injected CSS."""
    element_types = ("title", "header", "subheader", "caption", "markdown", "info", "error")
    return "\n".join(
        str(element.value)
        for element_type in element_types
        for element in app.get(element_type)
    )


def _png_upload() -> bytes:
    """Provide a sharp, normally lit payload that passes P4 and P5."""
    buffer = BytesIO()
    image = Image.new("L", (640, 480), color=0)
    pixels = image.load()
    for y in range(480):
        for x in range(640):
            pixels[x, y] = 255 if (x // 16 + y // 16) % 2 else 0
    image.convert("RGB").save(buffer, format="PNG")
    return buffer.getvalue()


def _flat_png_upload() -> bytes:
    """Provide a structurally valid but P5-unusable uniformly dark image."""
    buffer = BytesIO()
    Image.new("RGB", (640, 480), color=(3, 3, 3)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_app_starts_with_the_product_shell_and_stable_navigation() -> None:
    """Removing shell content or a destination makes the pre-model app unusable."""
    app = _run_app()

    assert not app.exception
    assert app.sidebar.radio[0].label == "Navigation"
    assert app.sidebar.radio[0].options == [
        "Assessment",
        "Model Comparison",
        "Model Insights",
        "Monitoring",
        "System / About",
    ]
    assert len(app.title) == 1
    brand_markup = next(
        element.value
        for element in app.sidebar.markdown
        if "cv-sidebar-brand" in element.value
    )
    assert "<h1" not in brand_markup
    assert "cv-status-pill" in _visible_text(app)

    visible_text = _visible_text(app)
    for required_copy in (
        "Auto Insurance Damage Assessment",
        "AI-assisted vehicle damage triage",
        "Prototype status: pre-model",
        "Decision-support only:",
        "Assessment",
    ):
        assert required_copy in visible_text


def test_assessment_offers_a_labelled_p3_upload_start_state() -> None:
    """Removing the uploader or guidance would leave the primary P3 flow unusable."""
    app = _run_app()

    assert not app.exception
    visible_text = _visible_text(app)
    assert len(app.file_uploader) == 1
    assert app.file_uploader[0].label == "Upload a vehicle image"
    assert len(app.button) == 1
    assert app.button[0].label == "Analyze damage"
    for required_copy in (
        "Vehicle Damage Assessment",
        "Upload a clear photo of the damaged vehicle for an AI-assisted preliminary assessment.",
        "JPG / JPEG / PNG / WEBP",
        "Maximum upload: 10 MB",
        "ensure the damaged area is visible",
        "avoid severe blur",
        "use adequate lighting",
        "include sufficient vehicle context",
    ):
        assert required_copy in visible_text
    assert "Upload is planned for P3." not in visible_text


def test_assessment_retains_a_valid_upload_and_keeps_analysis_as_a_safe_placeholder() -> None:
    """Dropping session state or rendering a prediction would break the P3 upload boundary."""
    app = _run_app()

    app.file_uploader[0].upload("vehicle-damage.png", _png_upload(), "image/png").run()
    assert not app.exception
    assert "Image ready for analysis" in _visible_text(app)
    assert len(app.image) == 1
    assert [button.label for button in app.button] == [
        "Analyze damage",
        "Upload another image",
    ]

    app.run()
    assert "Image ready for analysis" in _visible_text(app)

    app.button[0].click().run()
    visible_text = _visible_text(app)
    assert "Image passed structural and quality checks." in visible_text
    assert "No prediction is shown." in visible_text


def test_assessment_rejects_an_invalid_upload_without_rendering_a_preview() -> None:
    """Allowing an unsupported file to preview would bypass the P3 safety boundary."""
    app = _run_app()

    app.file_uploader[0].upload("vehicle-damage.jpg", b"not-an-image", "image/jpeg").run()

    assert not app.exception
    assert not app.image
    assert "We could not read this image." in _visible_text(app)
    assert [button.label for button in app.button] == ["Upload another image"]


def test_assessment_shows_a_corrective_message_for_an_undersized_supported_image() -> None:
    """Passing an undersized image to preview would bypass P4's configured geometry boundary."""
    buffer = BytesIO()
    Image.new("RGB", (8, 8), color=(32, 64, 96)).save(buffer, format="PNG")
    app = _run_app()

    app.file_uploader[0].upload("small.png", buffer.getvalue(), "image/png").run()

    assert not app.exception
    assert not app.image
    assert "at least 640 × 480 pixels" in _visible_text(app)


def test_assessment_keeps_a_p4_preview_but_blocks_analysis_for_p5_quality_failures() -> None:
    """Skipping P5 UI feedback would allow a known-unusable image to reach the placeholder action."""
    app = _run_app()

    app.file_uploader[0].upload("dark-flat.png", _flat_png_upload(), "image/png").run()

    assert not app.exception
    assert len(app.image) == 1
    visible_text = _visible_text(app)
    assert "The image appears too blurry for a reliable assessment." in visible_text
    assert "The image is too dark to assess reliably." in visible_text
    assert [button.label for button in app.button] == [
        "Analyze damage",
        "Upload another image",
    ]
    assert app.button[0].disabled is True


def test_assessment_reset_returns_to_the_empty_upload_state() -> None:
    """Leaving the old file after reset would prevent a user from starting another assessment."""
    app = _run_app()
    app.file_uploader[0].upload("vehicle-damage.png", _png_upload(), "image/png").run()

    app.button[1].click().run()

    assert not app.exception
    assert not app.image
    assert "Select a supported vehicle image to review it before analysis." in _visible_text(app)
    assert [button.label for button in app.button] == ["Analyze damage"]


def test_placeholder_pages_state_their_safe_pre_model_boundaries() -> None:
    """Replacing zero-data placeholders with metrics or predictions misrepresents the prototype."""
    app = _run_app()

    expected_pages = {
        "Model Comparison": "Model evaluation results are pending.",
        "Model Insights": "Evaluation results are not available yet.",
        "Monitoring": "No monitoring data is available in this development prototype.",
        "System / About": "Upload -> Validation -> Quality Gate -> Classifier -> "
        "YOLO localization -> Decision Engine -> Routing",
    }

    for destination, expected_copy in expected_pages.items():
        app.sidebar.radio[0].set_value(destination)
        app.run()

        assert not app.exception
        assert expected_copy in _visible_text(app)


def test_system_about_names_only_pending_candidates_and_localization() -> None:
    """Selected-model language would overstate the pre-model prototype's evidence."""
    app = _run_app()
    app.sidebar.radio[0].set_value("System / About")
    app.run()

    visible_text = _visible_text(app)
    for required_copy in (
        "Custom CNN",
        "MobileNetV2",
        "ViT-Tiny",
        "YOLOv8n",
        "Evaluation results are unavailable.",
        "Final selection is Pending AI model handoff.",
    ):
        assert required_copy in visible_text


def test_disclaimer_persists_on_every_navigation_destination() -> None:
    """A missing disclaimer on any page could make prototype content appear actionable."""
    app = _run_app()

    for destination in app.sidebar.radio[0].options:
        app.sidebar.radio[0].set_value(destination)
        app.run()

        assert "Decision-support only:" in _visible_text(app)


def test_page_renderer_registry_is_complete_and_dispatches_each_page() -> None:
    """A missing or mismatched renderer makes a navigation destination non-functional."""
    from src.ui.navigation import PAGE_ORDER, Page
    from src.ui.pages import assessment, model_comparison, model_insights, monitoring, system_about
    from src.ui.shell import PAGE_RENDERERS

    assert set(PAGE_RENDERERS) == set(PAGE_ORDER)
    assert PAGE_RENDERERS == {
        Page.ASSESSMENT: assessment.render,
        Page.MODEL_COMPARISON: model_comparison.render,
        Page.MODEL_INSIGHTS: model_insights.render,
        Page.MONITORING: monitoring.render,
        Page.SYSTEM_ABOUT: system_about.render,
    }


def test_page_configuration_precedes_rendering_and_uses_auto_sidebar() -> None:
    """Rendering before configuration or forcing expansion can obscure small-screen content."""
    tree = ast.parse((Path(__file__).resolve().parents[1] / "app.py").read_text())
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

    assert calls.index(page_config_call) < calls.index(render_app_call)
    assert {
        keyword.arg: keyword.value.value
        for keyword in page_config_call.keywords
        if isinstance(keyword.value, ast.Constant)
    }["initial_sidebar_state"] == "auto"
