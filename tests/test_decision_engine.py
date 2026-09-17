"""P8 policy-only routing tests over P5/P6/P7 contracts."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.adapters.mock import (
    MockClassifierAdapter,
    MockClassifierScenario,
    MockLocalizationAdapter,
    MockLocalizationScenario,
)
from src.config.labels import DamageTypeLabel, SeverityLabel
from src.config.policy import PolicySettings
from src.contracts.assessment import (
    BoundingBox,
    ClassificationResult,
    Detection,
    LocalizationResult,
    ModelExecutionMode,
    ModelMetadata,
    QualityCheckName,
    QualityCheckResult,
    QualityReasonCode,
    QualityReport,
    RoutingStatus,
)
from src.decision.engine import evaluate_routing
from src.decision.reasons import DecisionReasonCode


def _metadata() -> ModelMetadata:
    return ModelMetadata(
        name="p8-test-fixture",
        version=None,
        experiment_id=None,
        preprocessing_version=None,
        execution_mode=ModelExecutionMode.MOCK,
    )


def _quality_pass() -> QualityReport:
    return QualityReport(passed=True, checks=(), reasons=(), elapsed_ms=0.1)


def _quality_fail() -> QualityReport:
    check = QualityCheckResult(
        name=QualityCheckName.BLUR,
        passed=False,
        measured_value=0.1,
        threshold=0.75,
        code=QualityReasonCode.IMAGE_TOO_BLURRY,
        message="The image appears too blurry. Please upload a sharper photo.",
    )
    return QualityReport(
        passed=False,
        checks=(check,),
        reasons=(QualityReasonCode.IMAGE_TOO_BLURRY,),
        elapsed_ms=0.1,
    )


def _classification(
    severity: SeverityLabel = SeverityLabel.MINOR,
    damage_type: DamageTypeLabel = DamageTypeLabel.SCRATCH,
    severity_score: float | None = 0.9,
    damage_type_score: float | None = 0.9,
) -> ClassificationResult:
    return ClassificationResult(
        severity=severity,
        damage_type=damage_type,
        model=_metadata(),
        severity_score=severity_score,
        damage_type_score=damage_type_score,
    )


def _classification_unavailable() -> ClassificationResult:
    return ClassificationResult(
        severity=None,
        damage_type=None,
        model=_metadata(),
        available=False,
        unavailable_reason="CLASSIFIER_UNAVAILABLE",
    )


def _localization(
    *,
    damage_type: DamageTypeLabel = DamageTypeLabel.STRUCTURAL,
    score: float = 0.9,
    available: bool = True,
) -> LocalizationResult:
    if not available:
        return LocalizationResult(
            detections=(),
            model=_metadata(),
            available=False,
            unavailable_reason="LOCALIZATION_UNAVAILABLE",
        )
    return LocalizationResult(
        detections=(
            Detection(
                damage_type=damage_type,
                bounding_box=BoundingBox(0, 0, 10, 10),
                score=score,
            ),
        ),
        model=_metadata(),
    )


def _codes(decision) -> tuple[str, ...]:
    return tuple(reason.code for reason in decision.reasons)


@pytest.mark.parametrize(
    ("classification", "expected_status", "expected_codes"),
    [
        (
            _classification(),
            RoutingStatus.FAST_TRACK_ELIGIBLE,
            (DecisionReasonCode.MINOR_HIGH_SCORE_ELIGIBLE.value,),
        ),
        (
            _classification(severity=SeverityLabel.MODERATE),
            RoutingStatus.HUMAN_REVIEW_REQUIRED,
            (DecisionReasonCode.SEVERITY_MODERATE.value,),
        ),
        (
            _classification(severity=SeverityLabel.SEVERE),
            RoutingStatus.HUMAN_REVIEW_REQUIRED,
            (DecisionReasonCode.SEVERITY_SEVERE.value,),
        ),
        (
            _classification(severity_score=0.74),
            RoutingStatus.HUMAN_REVIEW_REQUIRED,
            (DecisionReasonCode.SEVERITY_SCORE_BELOW_THRESHOLD.value,),
        ),
        (
            _classification(damage_type_score=0.74),
            RoutingStatus.HUMAN_REVIEW_REQUIRED,
            (DecisionReasonCode.DAMAGE_TYPE_SCORE_BELOW_THRESHOLD.value,),
        ),
        (
            _classification(severity_score=None),
            RoutingStatus.HUMAN_REVIEW_REQUIRED,
            (DecisionReasonCode.SEVERITY_SCORE_MISSING.value,),
        ),
        (
            _classification(damage_type_score=None),
            RoutingStatus.HUMAN_REVIEW_REQUIRED,
            (DecisionReasonCode.DAMAGE_TYPE_SCORE_MISSING.value,),
        ),
    ],
)
def test_classification_policy_table(classification, expected_status, expected_codes) -> None:
    """Changing a policy branch or reason order must break its explicit routing outcome."""
    decision = evaluate_routing(classification, None, _quality_pass(), PolicySettings())

    assert decision.status is expected_status
    assert _codes(decision) == expected_codes


def test_quality_failure_has_highest_precedence_and_preserves_p5_guidance() -> None:
    """Model state must never override a request for a structurally valid but unusable photo."""
    decision = evaluate_routing(
        _classification_unavailable(),
        _localization(),
        _quality_fail(),
        PolicySettings(),
    )

    assert decision.status is RoutingStatus.RESUBMIT_IMAGE
    assert _codes(decision) == (
        DecisionReasonCode.IMAGE_QUALITY_FAILED.value,
        QualityReasonCode.IMAGE_TOO_BLURRY.value,
    )
    assert decision.reasons[1].message == "The image appears too blurry. Please upload a sharper photo."


def test_unavailable_classification_routes_to_review_before_localization_policy() -> None:
    """Localization cannot replace the required classifier contract."""
    decision = evaluate_routing(
        _classification_unavailable(),
        _localization(),
        _quality_pass(),
        PolicySettings(),
    )

    assert decision.status is RoutingStatus.HUMAN_REVIEW_REQUIRED
    assert _codes(decision) == (DecisionReasonCode.CLASSIFICATION_UNAVAILABLE.value,)


@pytest.mark.parametrize(
    "localization",
    [None, _localization(available=False), LocalizationResult((), _metadata())],
)
def test_missing_unavailable_or_empty_localization_does_not_block_minor_policy(localization) -> None:
    """Supplementary localization absence must not fabricate a review reason."""
    decision = evaluate_routing(
        _classification(), localization, _quality_pass(), PolicySettings()
    )

    assert decision.status is RoutingStatus.FAST_TRACK_ELIGIBLE


def test_only_configured_high_score_localization_conflict_requires_review() -> None:
    """A configured scratch-to-structural conflict matters only at the policy score boundary."""
    conflict = evaluate_routing(
        _classification(), _localization(score=0.8), _quality_pass(), PolicySettings()
    )
    below = evaluate_routing(
        _classification(), _localization(score=0.799999), _quality_pass(), PolicySettings()
    )
    unconfigured = evaluate_routing(
        _classification(),
        _localization(score=0.9),
        _quality_pass(),
        PolicySettings(conflict_pairs=()),
    )

    assert conflict.status is RoutingStatus.HUMAN_REVIEW_REQUIRED
    assert _codes(conflict) == (DecisionReasonCode.MODEL_SIGNAL_CONFLICT.value,)
    assert below.status is RoutingStatus.FAST_TRACK_ELIGIBLE
    assert unconfigured.status is RoutingStatus.FAST_TRACK_ELIGIBLE


def test_multiple_human_review_reasons_are_ordered_by_policy_precedence() -> None:
    """Overlapping review conditions must remain unambiguous and fully represented."""
    decision = evaluate_routing(
        _classification(
            severity=SeverityLabel.MODERATE,
            severity_score=0.3,
            damage_type_score=0.4,
        ),
        _localization(),
        _quality_pass(),
        PolicySettings(),
    )

    assert decision.status is RoutingStatus.HUMAN_REVIEW_REQUIRED
    assert _codes(decision) == (
        DecisionReasonCode.SEVERITY_MODERATE.value,
        DecisionReasonCode.SEVERITY_SCORE_BELOW_THRESHOLD.value,
        DecisionReasonCode.DAMAGE_TYPE_SCORE_BELOW_THRESHOLD.value,
        DecisionReasonCode.MODEL_SIGNAL_CONFLICT.value,
    )


def test_score_threshold_is_inclusive_and_immediately_below_requires_review() -> None:
    """Using a strict greater-than comparison would incorrectly reject exact-boundary scores."""
    at_boundary = evaluate_routing(
        _classification(severity_score=0.75, damage_type_score=0.75),
        None,
        _quality_pass(),
        PolicySettings(),
    )
    below_boundary = evaluate_routing(
        _classification(severity_score=0.749999, damage_type_score=0.75),
        None,
        _quality_pass(),
        PolicySettings(),
    )

    assert at_boundary.status is RoutingStatus.FAST_TRACK_ELIGIBLE
    assert below_boundary.status is RoutingStatus.HUMAN_REVIEW_REQUIRED


def test_policy_configuration_changes_behavior_without_engine_changes() -> None:
    """Calibrated handoff values must be replaceable through configuration alone."""
    classification = _classification(severity_score=0.85, damage_type_score=0.85)

    permissive = evaluate_routing(
        classification,
        None,
        _quality_pass(),
        PolicySettings(min_severity_score=0.8, min_damage_type_score=0.8),
    )
    strict = evaluate_routing(
        classification,
        None,
        _quality_pass(),
        PolicySettings(min_severity_score=0.9, min_damage_type_score=0.9),
    )

    assert permissive.status is RoutingStatus.FAST_TRACK_ELIGIBLE
    assert strict.status is RoutingStatus.HUMAN_REVIEW_REQUIRED


@dataclass(frozen=True)
class _AdapterImage:
    digest: str = "a" * 64
    width: int = 640
    height: int = 480


def test_engine_consumes_real_p7_mock_outputs_as_development_fixtures() -> None:
    """Changing P7 contract output must be caught at the P8 integration boundary."""
    image = _AdapterImage()
    classification = MockClassifierAdapter(
        MockClassifierScenario.NORMAL_MINOR_SCRATCH
    ).predict(image)
    localization = MockLocalizationAdapter(MockLocalizationScenario.UNAVAILABLE).localize(image)

    decision = evaluate_routing(
        classification, localization, _quality_pass(), PolicySettings()
    )

    assert classification.model.mock is True
    assert localization.model.mock is True
    assert decision.status is RoutingStatus.FAST_TRACK_ELIGIBLE


def test_invalid_scores_are_rejected_by_the_p6_contract_before_policy_evaluation() -> None:
    """P8 must not normalize malformed model signals or duplicate P6 validation."""
    with pytest.raises(ValueError, match="between 0 and 1"):
        _classification(severity_score=1.01)
