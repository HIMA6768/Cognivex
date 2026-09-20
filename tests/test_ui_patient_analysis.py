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
    assert all(profile[field] == 0.0 for field in track_c_fields[:50])
    assert all(profile[field] == "0" for field in track_c_fields[50:])
    request = build_patient_request(profile)
    assert request.requested_tracks == (AnalysisTrack.TRACK_A, AnalysisTrack.TRACK_B, AnalysisTrack.TRACK_C)
    assert request.features == profile


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
    next(button for button in app.button if button.label.startswith("Load synthetic demo profile")).click()
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
