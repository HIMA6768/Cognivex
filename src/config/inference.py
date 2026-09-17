"""P7 mock-inference switches with no model-runtime dependency."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InferenceSettings:
    """Control mock availability while real adapters remain pending AI handoff."""

    mock_inference: bool = True
    localization_enabled: bool = True
