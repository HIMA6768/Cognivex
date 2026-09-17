"""P7 deterministic mock adapter contracts using real P4 image outputs."""

from __future__ import annotations

from io import BytesIO

from PIL import Image

from src.adapters.interfaces import ClassifierAdapter, LocalizationAdapter
from src.adapters.mock import (
    MockClassifierAdapter,
    MockClassifierScenario,
    MockLocalizationAdapter,
    MockLocalizationScenario,
)
from src.config.labels import DamageTypeLabel, SeverityLabel
from src.contracts.assessment import ClassificationResult, LocalizationResult, ModelExecutionMode
from src.ui.upload_flow import ImageValidationLimits, validate_image_upload


def _p4_image():
    """Create a real P4-normalized image with dimensions meaningful to mock geometry."""
    payload = BytesIO()
    Image.new("RGB", (640, 480), color=(64, 96, 128)).save(payload, format="PNG")
    result = validate_image_upload(
        "vehicle.png",
        "image/png",
        payload.getvalue(),
        max_upload_bytes=1024 * 1024,
        limits=ImageValidationLimits(
            min_width=1,
            min_height=1,
            max_width=1024,
            max_height=1024,
            max_pixels=1_000_000,
        ),
    )
    assert result.image is not None
    return result.image


def test_mock_adapters_satisfy_the_stable_classifier_and_localizer_interfaces() -> None:
    """Removing either method would make future ONNX replacement incompatible with its caller."""
    assert isinstance(MockClassifierAdapter(), ClassifierAdapter)
    assert isinstance(MockLocalizationAdapter(), LocalizationAdapter)


def test_same_image_produces_the_same_complete_mock_classification_across_calls() -> None:
    """Using rerun-dependent randomness would make a mock result unusable for integration tests."""
    image = _p4_image()
    adapter = MockClassifierAdapter()

    first = adapter.predict(image)
    second = adapter.predict(image)

    assert first == second
    assert isinstance(first, ClassificationResult)
    assert first.available is True
    assert first.model.execution_mode is ModelExecutionMode.MOCK
    assert first.model.mock is True
    assert first.severity in SeverityLabel
    assert first.damage_type in DamageTypeLabel
    assert {score.label for score in first.all_scores} == set(SeverityLabel) | set(DamageTypeLabel)
    assert first.severity_score is not None
    assert first.damage_type_score is not None


def test_development_classification_scenarios_remain_explicit_and_unambiguously_mock() -> None:
    """Dropping scenario controls would block deterministic UI and integration fixtures."""
    image = _p4_image()
    normal = MockClassifierAdapter(MockClassifierScenario.NORMAL_MINOR_SCRATCH).predict(image)
    severe = MockClassifierAdapter(MockClassifierScenario.SEVERE).predict(image)
    low_score = MockClassifierAdapter(MockClassifierScenario.LOW_SCORE).predict(image)
    unavailable = MockClassifierAdapter(MockClassifierScenario.UNAVAILABLE).predict(image)

    assert (normal.severity, normal.damage_type) == (SeverityLabel.MINOR, DamageTypeLabel.SCRATCH)
    assert severe.severity is SeverityLabel.SEVERE
    assert low_score.severity_score is not None and low_score.severity_score < 0.5
    assert unavailable.available is False
    assert unavailable.severity is None
    assert unavailable.damage_type is None
    assert unavailable.unavailable_reason == "CLASSIFIER_UNAVAILABLE"
    assert all(result.model.mock is True for result in (normal, severe, low_score, unavailable))


def test_same_image_produces_deterministic_localization_and_valid_image_relative_boxes() -> None:
    """Invalid or changing boxes would make a future result surface unsafe to render."""
    image = _p4_image()
    adapter = MockLocalizationAdapter()

    first = adapter.localize(image)
    second = adapter.localize(image)

    assert first == second
    assert isinstance(first, LocalizationResult)
    assert first.available is True
    assert first.model.mock is True
    for detection in first.detections:
        box = detection.bounding_box
        assert 0 <= box.x_min < box.x_max <= image.width
        assert 0 <= box.y_min < box.y_max <= image.height
        assert detection.damage_type in DamageTypeLabel


def test_localization_scenarios_cover_zero_one_multiple_disabled_and_unavailable_paths() -> None:
    """Collapsing these distinct states would force callers to infer unavailable from fabricated detections."""
    image = _p4_image()
    one = MockLocalizationAdapter(MockLocalizationScenario.ONE).localize(image)
    zero = MockLocalizationAdapter(MockLocalizationScenario.NONE).localize(image)
    multiple = MockLocalizationAdapter(MockLocalizationScenario.MULTIPLE).localize(image)
    unavailable = MockLocalizationAdapter(MockLocalizationScenario.UNAVAILABLE).localize(image)
    disabled = MockLocalizationAdapter(localization_enabled=False).localize(image)

    assert len(one.detections) == 1 and one.available is True
    assert len(zero.detections) == 0 and zero.available is True
    assert len(multiple.detections) == 2 and multiple.available is True
    assert unavailable.available is False and unavailable.unavailable_reason == "LOCALIZATION_UNAVAILABLE"
    assert disabled.available is False and disabled.unavailable_reason == "LOCALIZATION_DISABLED"
    assert all(result.model.mock is True for result in (one, zero, multiple, unavailable, disabled))
