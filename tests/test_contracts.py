"""P6 framework-independent assessment-contract tests."""

from __future__ import annotations

import json
from io import BytesIO

import pytest
from PIL import Image

from src.config.labels import DamageTypeLabel, SeverityLabel
from src.contracts.assessment import (
    AssessmentResult,
    BoundingBox,
    ClassificationResult,
    Detection,
    LocalizationResult,
    ModelExecutionMode,
    ModelMetadata,
    RoutingDecision,
    RoutingReason,
    RoutingStatus,
    ValidationError,
    ValidationResult,
)
from src.ui.quality_gate import QualityReport, QualityThresholds, evaluate_quality
from src.ui.upload_flow import ImageValidationLimits, validate_image_upload


def _p4_image():
    """Return a real P4 image for adapter and P5 compatibility tests."""
    payload = BytesIO()
    image = Image.new("L", (64, 64), color=0)
    pixels = image.load()
    for y in range(64):
        for x in range(64):
            pixels[x, y] = 255 if (x // 4 + y // 4) % 2 else 0
    image.convert("RGB").save(payload, format="PNG")
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
    return result


def _metadata(mode: ModelExecutionMode = ModelExecutionMode.MOCK) -> ModelMetadata:
    return ModelMetadata(
        name="test-adapter",
        version=None,
        experiment_id=None,
        preprocessing_version=None,
        execution_mode=mode,
    )


def test_complete_assessment_contract_serializes_without_framework_objects() -> None:
    """Breaking a nested contract field would prevent future adapters from exchanging results."""
    validation = ValidationResult(
        passed=True,
        image_digest="a" * 64,
        width=640,
        height=480,
        normalized_mode="RGB",
        error=None,
    )
    quality = QualityReport(passed=True, checks=(), reasons=(), elapsed_ms=2.5)
    metadata = _metadata()
    classification = ClassificationResult(
        severity=SeverityLabel.MINOR,
        damage_type=DamageTypeLabel.DENT,
        model=metadata,
    )
    localization = LocalizationResult(
        detections=(
            Detection(
                damage_type=DamageTypeLabel.DENT,
                bounding_box=BoundingBox(x_min=10, y_min=20, x_max=110, y_max=120),
                score=None,
            ),
        ),
        model=metadata,
    )
    routing = RoutingDecision(
        status=RoutingStatus.HUMAN_REVIEW_REQUIRED,
        reasons=(
            RoutingReason(code="CONTRACT_EXAMPLE", message="A future policy supplied this reason."),
            RoutingReason(code="SECONDARY_CONTEXT", message="A second contract reason is preserved."),
        ),
    )

    result = AssessmentResult(
        validation=validation,
        quality=quality,
        classification=classification,
        localization=localization,
        routing=routing,
    )
    encoded = json.dumps(result.to_dict())
    decoded = json.loads(encoded)

    assert decoded["classification"]["severity"] == "minor"
    assert decoded["classification"]["damage_type"] == "dent"
    assert decoded["classification"]["model"]["execution_mode"] == "MOCK"
    assert decoded["localization"]["detections"][0]["bounding_box"]["x_max"] == 110
    assert decoded["routing"]["status"] == "HUMAN_REVIEW_REQUIRED"
    assert [reason["code"] for reason in decoded["routing"]["reasons"]] == [
        "CONTRACT_EXAMPLE",
        "SECONDARY_CONTEXT",
    ]


def test_routing_status_contract_preserves_all_future_policy_options() -> None:
    """Removing a status would make a later policy unable to return its contractually allowed result."""
    assert [status.value for status in RoutingStatus] == [
        "FAST_TRACK_ELIGIBLE",
        "HUMAN_REVIEW_REQUIRED",
        "RESUBMIT_IMAGE",
    ]


def test_routing_decision_requires_an_ordered_collection_of_typed_reasons() -> None:
    """A future policy must be able to preserve every independently actionable reason."""
    first = RoutingReason(code="IMAGE_QUALITY", message="Quality requires resubmission.")
    second = RoutingReason(code="MODEL_UNAVAILABLE", message="Model availability requires review.")

    decision = RoutingDecision(
        status=RoutingStatus.HUMAN_REVIEW_REQUIRED,
        reasons=(first, second),
    )

    assert decision.reasons == (first, second)
    with pytest.raises(ValueError):
        RoutingDecision(status=RoutingStatus.RESUBMIT_IMAGE, reasons=())
    with pytest.raises(TypeError):
        RoutingDecision(status=RoutingStatus.RESUBMIT_IMAGE, reasons=[first])  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        RoutingDecision(status=RoutingStatus.RESUBMIT_IMAGE, reasons=("not-a-reason",))  # type: ignore[arg-type]


def test_model_metadata_allows_pending_fields_and_distinguishes_mock_from_live() -> None:
    """Requiring invented handoff metadata would block safe mock adapters and future live adapters."""
    mock = _metadata(ModelExecutionMode.MOCK)
    live = _metadata(ModelExecutionMode.LIVE)

    assert mock.version is None
    assert mock.experiment_id is None
    assert mock.preprocessing_version is None
    assert mock.execution_mode is ModelExecutionMode.MOCK
    assert live.execution_mode is ModelExecutionMode.LIVE


@pytest.mark.parametrize(
    "factory",
    [
        lambda: ModelMetadata("", None, None, None, ModelExecutionMode.MOCK),
        lambda: BoundingBox(x_min=-1, y_min=0, x_max=1, y_max=1),
        lambda: BoundingBox(x_min=1, y_min=0, x_max=1, y_max=1),
        lambda: ClassificationResult("minor", DamageTypeLabel.DENT, _metadata()),
        lambda: RoutingReason(code="", message="Needs a code."),
    ],
)
def test_invalid_contract_values_are_rejected(factory) -> None:
    """Accepting malformed labels, geometry, or identifiers would make contracts unsafe to consume."""
    with pytest.raises((TypeError, ValueError)):
        factory()


def test_p4_result_adapts_to_the_canonical_validation_contract() -> None:
    """A mismapped P4 result would prevent the future pipeline from using existing validation output."""
    p4_result = _p4_image()

    contract = p4_result.to_contract()

    assert isinstance(contract, ValidationResult)
    assert contract.passed is True
    assert contract.image_digest == p4_result.image.digest
    assert (contract.width, contract.height) == (64, 64)
    assert contract.error is None


def test_failed_p4_result_adapts_to_a_typed_validation_error() -> None:
    """Dropping P4's stable code or safe copy would break invalid-upload handoff to later stages."""
    p4_result = validate_image_upload(
        "vehicle.jpg",
        "image/jpeg",
        b"",
        max_upload_bytes=1024 * 1024,
        limits=ImageValidationLimits(min_width=1, min_height=1),
    )

    contract = p4_result.to_contract()

    assert contract.passed is False
    assert contract.error == ValidationError(
        code="EMPTY_FILE", message="The selected file is empty. Choose another vehicle image."
    )


def test_p5_reports_are_the_canonical_quality_contracts() -> None:
    """Duplicating P5 types would create incompatible quality reports for later stages."""
    p4_result = _p4_image()
    assert p4_result.image is not None

    report = evaluate_quality(
        p4_result.image,
        QualityThresholds(
            min_laplacian_variance=80.0,
            min_mean_luminance=25.0,
            max_mean_luminance=230.0,
        ),
    )

    assert isinstance(report, QualityReport)
    assert json.loads(json.dumps(report.to_dict()))["passed"] is True


def test_assessment_contract_supports_partial_pipeline_results_before_p9() -> None:
    """Requiring P7/P8 output today would make a valid P4/P5-only assessment impossible to represent."""
    result = AssessmentResult(
        validation=ValidationResult(True, "b" * 64, 640, 480, "RGB", None),
        quality=None,
        classification=None,
        localization=None,
        routing=None,
    )

    assert result.to_dict()["classification"] is None
    assert result.to_dict()["routing"] is None
