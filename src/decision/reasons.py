"""Centralized stable P8 reason codes and user-safe explanations."""

from enum import StrEnum

from src.contracts.assessment import QualityReport, RoutingReason


class DecisionReasonCode(StrEnum):
    """Stable policy reason vocabulary; values are safe for serialization."""

    IMAGE_QUALITY_FAILED = "IMAGE_QUALITY_FAILED"
    CLASSIFICATION_UNAVAILABLE = "CLASSIFICATION_UNAVAILABLE"
    SEVERITY_MODERATE = "SEVERITY_MODERATE"
    SEVERITY_SEVERE = "SEVERITY_SEVERE"
    SEVERITY_SCORE_MISSING = "SEVERITY_SCORE_MISSING"
    SEVERITY_SCORE_BELOW_THRESHOLD = "SEVERITY_SCORE_BELOW_THRESHOLD"
    DAMAGE_TYPE_SCORE_MISSING = "DAMAGE_TYPE_SCORE_MISSING"
    DAMAGE_TYPE_SCORE_BELOW_THRESHOLD = "DAMAGE_TYPE_SCORE_BELOW_THRESHOLD"
    MODEL_SIGNAL_CONFLICT = "MODEL_SIGNAL_CONFLICT"
    MINOR_HIGH_SCORE_ELIGIBLE = "MINOR_HIGH_SCORE_ELIGIBLE"


_MESSAGES: dict[DecisionReasonCode, str] = {
    DecisionReasonCode.IMAGE_QUALITY_FAILED: (
        "The image did not pass the photo-quality checks. Please upload another image using "
        "the guidance provided."
    ),
    DecisionReasonCode.CLASSIFICATION_UNAVAILABLE: (
        "The damage classification is unavailable, so this assessment needs human review."
    ),
    DecisionReasonCode.SEVERITY_MODERATE: (
        "The preliminary severity signal is moderate, so this assessment needs human review."
    ),
    DecisionReasonCode.SEVERITY_SEVERE: (
        "The preliminary severity signal is severe, so this assessment needs human review."
    ),
    DecisionReasonCode.SEVERITY_SCORE_MISSING: (
        "The severity score is unavailable, so this assessment needs human review."
    ),
    DecisionReasonCode.SEVERITY_SCORE_BELOW_THRESHOLD: (
        "The severity signal is not strong enough for the development fast-track policy."
    ),
    DecisionReasonCode.DAMAGE_TYPE_SCORE_MISSING: (
        "The damage-type score is unavailable, so this assessment needs human review."
    ),
    DecisionReasonCode.DAMAGE_TYPE_SCORE_BELOW_THRESHOLD: (
        "The damage-type signal is not strong enough for the development fast-track policy."
    ),
    DecisionReasonCode.MODEL_SIGNAL_CONFLICT: (
        "The classification and localization signals conflict, so this assessment needs human review."
    ),
    DecisionReasonCode.MINOR_HIGH_SCORE_ELIGIBLE: (
        "This minor case meets the provisional development criteria for fast-track eligibility."
    ),
}


def routing_reason(code: DecisionReasonCode) -> RoutingReason:
    """Build a P6 routing reason from the centralized P8 vocabulary."""
    return RoutingReason(code=code.value, message=_MESSAGES[code])


def quality_failure_reasons(report: QualityReport) -> tuple[RoutingReason, ...]:
    """Preserve ordered, actionable P5 failures after the P8 quality precedence reason."""
    details = tuple(
        RoutingReason(code=check.code.value, message=check.message)
        for check in report.checks
        if check.code is not None and check.message is not None
    )
    return (routing_reason(DecisionReasonCode.IMAGE_QUALITY_FAILED), *details)
