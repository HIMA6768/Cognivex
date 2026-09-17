"""Narrow, configuration-owned P8 classifier/localizer conflict checks."""

from src.config.policy import PolicySettings
from src.contracts.assessment import ClassificationResult, LocalizationResult


def has_model_signal_conflict(
    classification: ClassificationResult,
    localization: LocalizationResult | None,
    policy: PolicySettings,
) -> bool:
    """Return true only for an explicit pair with a sufficiently strong localization signal."""
    if not classification.available or localization is None or not localization.available:
        return False
    configured_pairs = frozenset(policy.conflict_pairs)
    return any(
        detection.score is not None
        and detection.score >= policy.min_localization_conflict_score
        and (classification.damage_type, detection.damage_type) in configured_pairs
        for detection in localization.detections
    )
