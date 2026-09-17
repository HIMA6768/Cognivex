from __future__ import annotations

import pytest

from src.config import PolicySettings
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
    assert settings.upload.max_upload_mb == 10
    assert settings.upload.max_upload_bytes == 10 * 1024 * 1024
    assert settings.thresholds.max_image_width == 8192
    assert settings.thresholds.max_image_height == 8192
    assert settings.thresholds.max_image_pixels == 40_000_000
    assert settings.thresholds.min_laplacian_variance == 80.0
    assert settings.thresholds.min_tile_laplacian_variance == 40.0
    assert settings.thresholds.min_usable_sharp_tile_ratio == 0.75
    assert settings.thresholds.min_mean_luminance == 25.0
    assert settings.thresholds.min_median_luminance == 25.0
    assert settings.thresholds.dark_pixel_luminance == 20.0
    assert settings.thresholds.max_dark_pixel_ratio == 0.65
    assert settings.thresholds.max_mean_luminance == 230.0
    assert settings.thresholds.max_median_luminance == 230.0
    assert settings.thresholds.bright_pixel_luminance == 240.0
    assert settings.thresholds.max_bright_pixel_ratio == 0.65
    assert settings.inference.mock_inference is True
    assert settings.inference.localization_enabled is True
    assert settings.policy.min_severity_score == 0.75
    assert settings.policy.min_damage_type_score == 0.75
    assert settings.policy.min_localization_conflict_score == 0.8
    assert settings.policy.conflict_pairs == (
        (DamageTypeLabel.SCRATCH, DamageTypeLabel.STRUCTURAL),
    )


def test_environment_overrides_are_parsed() -> None:
    settings = AppSettings.from_env(
        {
            "COGNIVEX_ENVIRONMENT": "production",
            "COGNIVEX_DEBUG": "false",
            "COGNIVEX_MODEL_PATH": "models/damage-classifier.onnx",
            "COGNIVEX_MODEL_CONFIDENCE": "0.85",
            "COGNIVEX_MIN_IMAGE_WIDTH": "1024",
            "COGNIVEX_MIN_IMAGE_HEIGHT": "768",
            "COGNIVEX_MAX_UPLOAD_MB": "16",
            "COGNIVEX_MAX_IMAGE_WIDTH": "4096",
            "COGNIVEX_MAX_IMAGE_HEIGHT": "3072",
            "COGNIVEX_MAX_IMAGE_PIXELS": "12000000",
            "COGNIVEX_MIN_LAPLACIAN_VARIANCE": "120.5",
            "COGNIVEX_MIN_TILE_LAPLACIAN_VARIANCE": "75.5",
            "COGNIVEX_MIN_USABLE_SHARP_TILE_RATIO": "0.8",
            "COGNIVEX_MIN_MEAN_LUMINANCE": "35",
            "COGNIVEX_MIN_MEDIAN_LUMINANCE": "40",
            "COGNIVEX_DARK_PIXEL_LUMINANCE": "30",
            "COGNIVEX_MAX_DARK_PIXEL_RATIO": "0.55",
            "COGNIVEX_MAX_MEAN_LUMINANCE": "220",
            "COGNIVEX_MAX_MEDIAN_LUMINANCE": "210",
            "COGNIVEX_BRIGHT_PIXEL_LUMINANCE": "235",
            "COGNIVEX_MAX_BRIGHT_PIXEL_RATIO": "0.45",
            "COGNIVEX_MOCK_INFERENCE": "false",
            "COGNIVEX_LOCALIZATION_ENABLED": "false",
            "COGNIVEX_POLICY_MIN_SEVERITY_SCORE": "0.82",
            "COGNIVEX_POLICY_MIN_DAMAGE_TYPE_SCORE": "0.79",
            "COGNIVEX_POLICY_MIN_LOCALIZATION_CONFLICT_SCORE": "0.91",
        }
    )

    assert settings.environment == "production"
    assert settings.debug is False
    assert settings.model_path == "models/damage-classifier.onnx"
    assert settings.thresholds.model_confidence == 0.85
    assert settings.thresholds.min_image_width == 1024
    assert settings.thresholds.min_image_height == 768
    assert settings.upload.max_upload_mb == 16
    assert settings.thresholds.max_image_width == 4096
    assert settings.thresholds.max_image_height == 3072
    assert settings.thresholds.max_image_pixels == 12_000_000
    assert settings.thresholds.min_laplacian_variance == 120.5
    assert settings.thresholds.min_tile_laplacian_variance == 75.5
    assert settings.thresholds.min_usable_sharp_tile_ratio == 0.8
    assert settings.thresholds.min_mean_luminance == 35.0
    assert settings.thresholds.min_median_luminance == 40.0
    assert settings.thresholds.dark_pixel_luminance == 30.0
    assert settings.thresholds.max_dark_pixel_ratio == 0.55
    assert settings.thresholds.max_mean_luminance == 220.0
    assert settings.thresholds.max_median_luminance == 210.0
    assert settings.thresholds.bright_pixel_luminance == 235.0
    assert settings.thresholds.max_bright_pixel_ratio == 0.45
    assert settings.inference.mock_inference is False
    assert settings.inference.localization_enabled is False
    assert settings.policy.min_severity_score == 0.82
    assert settings.policy.min_damage_type_score == 0.79
    assert settings.policy.min_localization_conflict_score == 0.91


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
        ("COGNIVEX_MAX_UPLOAD_MB", "0"),
        ("COGNIVEX_MAX_UPLOAD_MB", "many"),
        ("COGNIVEX_MAX_IMAGE_WIDTH", "0"),
        ("COGNIVEX_MAX_IMAGE_HEIGHT", "-1"),
        ("COGNIVEX_MAX_IMAGE_PIXELS", "many"),
        ("COGNIVEX_MIN_LAPLACIAN_VARIANCE", "0"),
        ("COGNIVEX_MIN_TILE_LAPLACIAN_VARIANCE", "0"),
        ("COGNIVEX_MIN_USABLE_SHARP_TILE_RATIO", "1.01"),
        ("COGNIVEX_MIN_MEAN_LUMINANCE", "-1"),
        ("COGNIVEX_MIN_MEDIAN_LUMINANCE", "-1"),
        ("COGNIVEX_MAX_MEAN_LUMINANCE", "bright"),
        ("COGNIVEX_MAX_MEDIAN_LUMINANCE", "bright"),
        ("COGNIVEX_MAX_DARK_PIXEL_RATIO", "1.01"),
        ("COGNIVEX_MAX_BRIGHT_PIXEL_RATIO", "-0.01"),
        ("COGNIVEX_POLICY_MIN_SEVERITY_SCORE", "1.01"),
        ("COGNIVEX_POLICY_MIN_DAMAGE_TYPE_SCORE", "NaN"),
        ("COGNIVEX_POLICY_MIN_LOCALIZATION_CONFLICT_SCORE", "low"),
    ],
)
def test_zero_negative_or_invalid_image_dimensions_raise_configuration_error(
    variable: str, value: str
) -> None:
    with pytest.raises(ConfigurationError, match=variable):
        AppSettings.from_env({variable: value})


def test_invalid_luminance_range_raises_configuration_error() -> None:
    """A reversed quality range would make P5's result impossible to interpret."""
    with pytest.raises(ConfigurationError, match="COGNIVEX_MIN_MEAN_LUMINANCE"):
        AppSettings.from_env(
            {
                "COGNIVEX_MIN_MEAN_LUMINANCE": "231",
                "COGNIVEX_MAX_MEAN_LUMINANCE": "230",
            }
        )


def test_luminance_thresholds_accept_the_full_zero_to_255_measurement_range() -> None:
    """Rejecting a zero bound would prevent a legitimate configuration of the metric domain."""
    settings = AppSettings.from_env(
        {
            "COGNIVEX_MIN_MEAN_LUMINANCE": "0",
            "COGNIVEX_MAX_MEAN_LUMINANCE": "255",
        }
    )

    assert settings.thresholds.min_mean_luminance == 0.0
    assert settings.thresholds.max_mean_luminance == 255.0


def test_policy_settings_reject_invalid_conflict_pairs() -> None:
    """Malformed or self-conflicting labels would make policy behavior ambiguous."""
    with pytest.raises(ValueError, match="different canonical damage-type labels"):
        PolicySettings(
            conflict_pairs=((DamageTypeLabel.SCRATCH, DamageTypeLabel.SCRATCH),)
        )
    with pytest.raises(TypeError, match="canonical damage-type labels"):
        PolicySettings(conflict_pairs=(("scratch", DamageTypeLabel.STRUCTURAL),))  # type: ignore[arg-type]
