"""Pure precedence-ordered P8 routing policy."""

from src.config.labels import SeverityLabel
from src.config.policy import PolicySettings
from src.contracts.assessment import (
    ClassificationResult,
    LocalizationResult,
    QualityReport,
    RoutingDecision,
    RoutingReason,
    RoutingStatus,
)

from .conflicts import has_model_signal_conflict
from .reasons import DecisionReasonCode, quality_failure_reasons, routing_reason


def _score_reason(
    score: float | None,
    threshold: float,
    missing_code: DecisionReasonCode,
    below_code: DecisionReasonCode,
) -> RoutingReason | None:
    if score is None:
        return routing_reason(missing_code)
    if score < threshold:
        return routing_reason(below_code)
    return None


def evaluate_routing(
    classification: ClassificationResult,
    localization: LocalizationResult | None,
    quality_report: QualityReport,
    policy: PolicySettings,
) -> RoutingDecision:
    """Return a deterministic decision-support route using explicit P8 precedence."""
    if not quality_report.passed:
        return RoutingDecision(
            status=RoutingStatus.RESUBMIT_IMAGE,
            reasons=quality_failure_reasons(quality_report),
        )

    if not classification.available:
        return RoutingDecision(
            status=RoutingStatus.HUMAN_REVIEW_REQUIRED,
            reasons=(routing_reason(DecisionReasonCode.CLASSIFICATION_UNAVAILABLE),),
        )

    reasons: list[RoutingReason] = []
    if classification.severity is SeverityLabel.MODERATE:
        reasons.append(routing_reason(DecisionReasonCode.SEVERITY_MODERATE))
    elif classification.severity is SeverityLabel.SEVERE:
        reasons.append(routing_reason(DecisionReasonCode.SEVERITY_SEVERE))

    severity_score_reason = _score_reason(
        classification.severity_score,
        policy.min_severity_score,
        DecisionReasonCode.SEVERITY_SCORE_MISSING,
        DecisionReasonCode.SEVERITY_SCORE_BELOW_THRESHOLD,
    )
    if severity_score_reason is not None:
        reasons.append(severity_score_reason)

    damage_type_score_reason = _score_reason(
        classification.damage_type_score,
        policy.min_damage_type_score,
        DecisionReasonCode.DAMAGE_TYPE_SCORE_MISSING,
        DecisionReasonCode.DAMAGE_TYPE_SCORE_BELOW_THRESHOLD,
    )
    if damage_type_score_reason is not None:
        reasons.append(damage_type_score_reason)

    if has_model_signal_conflict(classification, localization, policy):
        reasons.append(routing_reason(DecisionReasonCode.MODEL_SIGNAL_CONFLICT))

    if reasons:
        return RoutingDecision(
            status=RoutingStatus.HUMAN_REVIEW_REQUIRED,
            reasons=tuple(reasons),
        )

    return RoutingDecision(
        status=RoutingStatus.FAST_TRACK_ELIGIBLE,
        reasons=(routing_reason(DecisionReasonCode.MINOR_HIGH_SCORE_ELIGIBLE),),
    )
