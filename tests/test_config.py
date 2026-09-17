from __future__ import annotations

import pytest

from src.config import AppSettings, ConfigurationError


def test_development_defaults_are_domain_neutral() -> None:
    settings = AppSettings.from_env({})

    assert settings.environment == "development"
    assert settings.debug is True


def test_environment_and_debug_overrides_are_parsed() -> None:
    settings = AppSettings.from_env(
        {
            "COGNIVEX_ENVIRONMENT": "production",
            "COGNIVEX_DEBUG": "false",
        }
    )

    assert settings.environment == "production"
    assert settings.debug is False


def test_blank_environment_uses_the_safe_default() -> None:
    settings = AppSettings.from_env({"COGNIVEX_ENVIRONMENT": "   "})

    assert settings.environment == "development"


@pytest.mark.parametrize("value", ["1", "yes", "sometimes"])
def test_invalid_debug_values_raise_a_clear_configuration_error(value: str) -> None:
    with pytest.raises(ConfigurationError, match="COGNIVEX_DEBUG must be true or false"):
        AppSettings.from_env({"COGNIVEX_DEBUG": value})


def test_blank_debug_uses_the_safe_default() -> None:
    assert AppSettings.from_env({"COGNIVEX_DEBUG": ""}).debug is True
