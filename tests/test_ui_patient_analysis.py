"""Unified OncoMap Patient Analysis contracts and presentation safety tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from src.contracts.inference import AnalysisTrack
from src.services.analysis import AnalysisService
from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]


def test_patient_analysis_builds_one_exact_r9_request_and_a_labelled_demo_profile() -> None:
    assert importlib.util.find_spec("src.ui.components.patient_analysis") is not None
    from src.ui.components.patient_analysis import build_patient_request, synthetic_demo_profile

    service = AnalysisService.from_canonical_artifacts(ROOT)
    track_a_fields = service.registry.track_a.required_fields
    track_c_fields = service.registry.track_c.required_fields
    profile = synthetic_demo_profile(track_a_fields, track_c_fields[:50], track_c_fields[50:])

    assert set(profile) == set(service.allowed_input_fields)
    assert len(profile) == 75
    assert any(profile[field] != 0.0 for field in track_c_fields[:50])
    assert all(isinstance(profile[field], float) for field in track_c_fields[:50])
    assert all(profile[field] != "0" for field in track_c_fields[50:])
    request = build_patient_request(profile)
    assert request.requested_tracks == (AnalysisTrack.TRACK_A, AnalysisTrack.TRACK_B, AnalysisTrack.TRACK_C)
    assert request.features["tumor_size"] == 24.0
    assert profile["tumor_size"] == 2.4
    assert {field: request.features[field] for field in track_c_fields} == {
        field: profile[field] for field in track_c_fields
    }


def test_patient_analysis_keeps_partial_values_for_r9_readiness() -> None:
    assert importlib.util.find_spec("src.ui.components.patient_analysis") is not None
    from src.ui.components.patient_analysis import build_patient_request

    request = build_patient_request({"age_at_diagnosis": 52.0})

    assert request.features == {"age_at_diagnosis": 52.0}
    assert request.requested_tracks == (AnalysisTrack.TRACK_A, AnalysisTrack.TRACK_B, AnalysisTrack.TRACK_C)


def test_patient_analysis_demo_reaches_result_first_survival_and_subtype_output() -> None:
    app = AppTest.from_file(ROOT / "app.py")
    app.run(timeout=30)
    app.sidebar.radio[1].set_value("Patient Analysis")
    app.run(timeout=30)

    assert not app.exception
    assert "Step 1: Clinical details" in str(app.subheader[0].value)
    next(button for button in app.button if button.label.startswith("Load full synthetic demo")).click()
    app.run(timeout=30)
    next(button for button in app.button if button.label == "Save and continue").click()
    app.run(timeout=30)
    assert "Step 2: Genomic profile" in str(app.subheader[0].value)
    assert len(app.number_input) == 50
    assert len(app.text_input) == 18
    next(button for button in app.button if button.label == "Save and continue").click()
    app.run(timeout=30)
    assert "Step 3: Review / validate" in str(app.subheader[0].value)
    next(button for button in app.button if button.label == "Continue to run").click()
    app.run(timeout=30)
    next(button for button in app.button if button.label == "Run analysis").click()
    app.run(timeout=30)

    assert not app.exception
    visible_markdown = "\n".join(str(item.value) for item in app.markdown)
    assert "1 year" in visible_markdown.lower()
    assert "3 years" in visible_markdown.lower()
    assert "5 years" in visible_markdown.lower()
    assert "Predicted subtype" in visible_markdown
    assert any(expander.label == "Technical details" for expander in app.expander)


def _patient_analysis_app() -> AppTest:
    app = AppTest.from_file(ROOT / "app.py")
    app.run(timeout=30)
    app.sidebar.radio[1].set_value("Patient Analysis")
    app.run(timeout=30)
    return app


def _button(app: AppTest, label: str):
    return next(button for button in app.button if button.label == label)


def _input(app: AppTest, label: str):
    return next(widget for widget in (*app.number_input, *app.text_input) if widget.label == label)


def _complete_clinical_values(app: AppTest) -> None:
    _input(app, "Age at diagnosis (years)").set_value(55.0)
    _input(app, "Tumor size (cm)").set_value(2.4)
    _input(app, "Positive lymph nodes").set_value(1.0)
    next(widget for widget in app.selectbox if widget.label == "Tumor stage").set_value("2")
    next(widget for widget in app.selectbox if widget.label == "ER status").set_value("Positive")
    next(widget for widget in app.selectbox if widget.label == "PR status").set_value("Positive")
    next(widget for widget in app.selectbox if widget.label == "HER2 status").set_value("Negative")
    app.run(timeout=30)


def _advance_demo_to_results(app: AppTest) -> None:
    _button(app, "Load full synthetic demo — clinical + genomic (not patient data)").click()
    app.run(timeout=30)
    _button(app, "Save and continue").click()
    app.run(timeout=30)
    _button(app, "Save and continue").click()
    app.run(timeout=30)
    _button(app, "Continue to run").click()
    app.run(timeout=30)
    _button(app, "Run analysis").click()
    app.run(timeout=30)


def test_fresh_session_keeps_genomic_fields_absent_and_only_clinical_track_ready() -> None:
    app = _patient_analysis_app()
    _complete_clinical_values(app)
    _button(app, "Save and continue").click()
    app.run(timeout=30)

    assert all(widget.value is None for widget in app.number_input)
    assert all(widget.value == "" for widget in app.text_input)
    _button(app, "Save and continue").click()
    app.run(timeout=30)
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics["Clinical fields"] == "7/7"
    assert metrics["Expression fields"] == "0/50"
    assert metrics["Mutation fields"] == "0/18"
    _button(app, "Continue to run").click()
    app.run(timeout=30)
    _button(app, "Run analysis").click()
    app.run(timeout=30)
    assert any("Primary result: Clinical-only prognosis" in str(item.value) for item in app.caption)
    assert not any(metric.label == "Predicted subtype" for metric in app.metric)
    warnings = "\n".join(str(item.value) for item in app.warning)
    assert "Genomic profile incomplete. Clinical + genomic prognosis and molecular subtype classification require all 68 genomic inputs." in warnings
    assert any(expander.label == "View missing genomic fields" for expander in app.expander)


def test_loading_demo_reflects_every_genomic_value_in_visible_widgets() -> None:
    app = _patient_analysis_app()
    _button(app, "Load full synthetic demo — clinical + genomic (not patient data)").click()
    app.run(timeout=30)
    _button(app, "Save and continue").click()
    app.run(timeout=30)

    assert any(widget.value != 0.0 for widget in app.number_input)
    assert all(widget.value not in (None, "") for widget in app.text_input)
    assert any(button.label == "Load synthetic genomic demo" for button in app.button)
    assert any(button.label == "Clear genomic data" for button in app.button)
    _button(app, "Save and continue").click()
    app.run(timeout=30)
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics["Expression fields"] == "50/50"
    assert metrics["Mutation fields"] == "18/18"


def test_genomic_demo_is_explicit_and_clear_then_reload_preserves_absent_vs_zero() -> None:
    app = _patient_analysis_app()
    _complete_clinical_values(app)
    _button(app, "Save and continue").click()
    app.run(timeout=30)

    assert all(widget.value is None for widget in app.number_input)
    assert all(widget.value == "" for widget in app.text_input)

    _button(app, "Load synthetic genomic demo").click()
    app.run(timeout=30)
    assert len(app.number_input) == 50
    assert len(app.text_input) == 18
    assert any(widget.value != 0.0 for widget in app.number_input)
    assert all(widget.value not in (None, "") for widget in app.text_input)

    _button(app, "Clear genomic data").click()
    app.run(timeout=30)
    assert all(widget.value is None for widget in app.number_input)
    assert all(widget.value == "" for widget in app.text_input)

    _button(app, "Load synthetic genomic demo").click()
    app.run(timeout=30)
    assert any(widget.value != 0.0 for widget in app.number_input)
    assert all(widget.value not in (None, "") for widget in app.text_input)


def test_explicit_genomic_zero_is_present_but_untouched_fields_remain_absent() -> None:
    app = _patient_analysis_app()
    _complete_clinical_values(app)
    _button(app, "Save and continue").click()
    app.run(timeout=30)
    app.number_input[0].set_value(0.0)
    app.run(timeout=30)
    _button(app, "Save and continue").click()
    app.run(timeout=30)

    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics["Expression fields"] == "1/50"
    assert metrics["Mutation fields"] == "0/18"


def test_build_patient_request_converts_ui_centimetres_to_frozen_mm_contract() -> None:
    from src.ui.components.patient_analysis import build_patient_request

    request = build_patient_request({"tumor_size": 2.4, "age_at_diagnosis": 55.0})

    assert request.features == {"tumor_size": 24.0, "age_at_diagnosis": 55.0}


def test_clearing_visible_demo_genomic_values_removes_them_from_review() -> None:
    app = _patient_analysis_app()
    _button(app, "Load full synthetic demo — clinical + genomic (not patient data)").click()
    app.run(timeout=30)
    _button(app, "Save and continue").click()
    app.run(timeout=30)
    app.number_input[0].set_value(None)
    app.text_input[0].set_value("")
    app.run(timeout=30)
    _button(app, "Save and continue").click()
    app.run(timeout=30)

    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics["Expression fields"] == "49/50"
    assert metrics["Mutation fields"] == "17/18"


def test_edit_inputs_preserves_current_values_and_invalidates_result() -> None:
    app = _patient_analysis_app()
    _advance_demo_to_results(app)
    assert any(button.label == "← Edit inputs" for button in app.button)

    _button(app, "← Edit inputs").click()
    app.run(timeout=30)

    assert "Step 1: Clinical details" in str(app.subheader[0].value)
    assert _input(app, "Age at diagnosis (years)").value == 55.0
    assert "Step 5: Results" not in "\n".join(str(item.value) for item in app.subheader)


def test_start_new_analysis_clears_patient_values_and_previous_result() -> None:
    app = _patient_analysis_app()
    _advance_demo_to_results(app)
    assert any(button.label == "Start new analysis" for button in app.button)

    _button(app, "Start new analysis").click()
    app.run(timeout=30)

    assert "Step 1: Clinical details" in str(app.subheader[0].value)
    assert _input(app, "Age at diagnosis (years)").value is None
    assert "Step 5: Results" not in "\n".join(str(item.value) for item in app.subheader)
