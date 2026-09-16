from __future__ import annotations

import pytest

from src.config.labels import DamageTypeLabel, SeverityLabel
from src.config.settings import AppSettings, ConfigurationError


def test_canonical_label_values_are_stable() -> None:
    assert [label.value for label in SeverityLabel] == ["minor", "moderate", "severe"]
    assert [label.value for label in DamageTypeLabel] == [
        "dent",
        "scratch",
        "broken_glass",
        "structural",
    ]


def test_development_defaults_leave_model_configuration_unset() -> None:
    settings = AppSettings.from_env({})

    assert settings.environment == "development"
    assert settings.debug is True
    assert settings.model_path is None
    assert settings.thresholds.model_confidence is None
    assert settings.thresholds.min_image_width == 640
    assert settings.thresholds.min_image_height == 480


def test_environment_overrides_are_parsed() -> None:
    settings = AppSettings.from_env(
        {
            "COGNIVEX_ENVIRONMENT": "production",
            "COGNIVEX_DEBUG": "false",
            "COGNIVEX_MODEL_PATH": "models/damage-classifier.onnx",
            "COGNIVEX_MODEL_CONFIDENCE": "0.85",
            "COGNIVEX_MIN_IMAGE_WIDTH": "1024",
            "COGNIVEX_MIN_IMAGE_HEIGHT": "768",
        }
    )

    assert settings.environment == "production"
    assert settings.debug is False
    assert settings.model_path == "models/damage-classifier.onnx"
    assert settings.thresholds.model_confidence == 0.85
    assert settings.thresholds.min_image_width == 1024
    assert settings.thresholds.min_image_height == 768


def test_blank_optional_model_fields_are_unset() -> None:
    settings = AppSettings.from_env(
        {
            "COGNIVEX_MODEL_PATH": "   ",
            "COGNIVEX_MODEL_CONFIDENCE": "\t",
        }
    )

    assert settings.model_path is None
    assert settings.thresholds.model_confidence is None


@pytest.mark.parametrize(
    ("environ", "variable"),
    [
        ({"COGNIVEX_DEBUG": "sometimes"}, "COGNIVEX_DEBUG"),
        ({"COGNIVEX_MODEL_CONFIDENCE": "high"}, "COGNIVEX_MODEL_CONFIDENCE"),
        ({"COGNIVEX_MIN_IMAGE_WIDTH": "wide"}, "COGNIVEX_MIN_IMAGE_WIDTH"),
    ],
)
def test_invalid_boolean_and_numeric_values_raise_configuration_error(
    environ: dict[str, str], variable: str
) -> None:
    with pytest.raises(ConfigurationError, match=variable):
        AppSettings.from_env(environ)


@pytest.mark.parametrize("value", ["-0.01", "1.01", "NaN", "inf"])
def test_out_of_range_or_non_finite_model_confidence_raises_configuration_error(
    value: str,
) -> None:
    with pytest.raises(ConfigurationError, match="COGNIVEX_MODEL_CONFIDENCE"):
        AppSettings.from_env({"COGNIVEX_MODEL_CONFIDENCE": value})


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("COGNIVEX_MIN_IMAGE_WIDTH", "0"),
        ("COGNIVEX_MIN_IMAGE_WIDTH", "-1"),
        ("COGNIVEX_MIN_IMAGE_HEIGHT", "0"),
        ("COGNIVEX_MIN_IMAGE_HEIGHT", "-1"),
        ("COGNIVEX_MIN_IMAGE_HEIGHT", "tall"),
    ],
)
def test_zero_negative_or_invalid_image_dimensions_raise_configuration_error(
    variable: str, value: str
) -> None:
    with pytest.raises(ConfigurationError, match=variable):
        AppSettings.from_env({variable: value})
