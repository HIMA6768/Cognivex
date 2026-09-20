from __future__ import annotations

import math

import pytest

from src.contracts.inference import (
    AggregateAnalysisError,
    AnalysisRequest,
    AnalysisTrack,
    FROZEN_SUBTYPE_CLASS_ORDER,
    PrognosisResult,
    PrognosticFeatureAnalysisOutcome,
    RequestError,
    ResultLineage,
    SubtypeClassificationResult,
    SurvivalProbabilityEstimates,
    TrackError,
    TrackOutcome,
    TrackReadinessState,
)


def _lineage(track: AnalysisTrack = AnalysisTrack.TRACK_A) -> ResultLineage:
    return ResultLineage(track, "experiment", "r9-v1", "a" * 64)


def _prognosis() -> PrognosisResult:
    return PrognosisResult(
        _lineage(), "log_partial_hazard", "Model log relative hazard score", 0.25,
        "Model-relative log partial hazard; not an absolute survival probability, mortality probability, risk category, treatment recommendation, or clinical prognosis.",
    )


def test_ready_track_outcome_requires_result_and_no_error() -> None:
    with pytest.raises(ValueError, match="READY"):
        TrackOutcome(AnalysisTrack.TRACK_A, TrackReadinessState.READY, None, None)

    with pytest.raises(ValueError, match="non-ready"):
        TrackOutcome(
            AnalysisTrack.TRACK_A,
            TrackReadinessState.INVALID_INPUT,
            _prognosis(),
            TrackError("INVALID_INPUT", "Invalid input", AnalysisTrack.TRACK_A),
        )


def test_subtype_result_requires_exact_frozen_order_and_normalized_probabilities() -> None:
    with pytest.raises(ValueError, match="class_order"):
        SubtypeClassificationResult(_lineage(AnalysisTrack.TRACK_C), "Basal", ("Basal",), (1.0,))

    with pytest.raises(ValueError, match="sum"):
        SubtypeClassificationResult(
            _lineage(AnalysisTrack.TRACK_C), "Basal", FROZEN_SUBTYPE_CLASS_ORDER,
            (0.5,) * 6,
        )

    result = SubtypeClassificationResult(
        _lineage(AnalysisTrack.TRACK_C), "Basal", FROZEN_SUBTYPE_CLASS_ORDER,
        (1.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    )
    assert result.predicted_class == "Basal"


def test_request_error_serializes_field_names_without_feature_values() -> None:
    result = RequestError("UNKNOWN_FIELD", "Unknown field", ("Tumor_Size",))
    assert result.to_dict() == {
        "code": "UNKNOWN_FIELD", "message": "Unknown field", "fields": ["Tumor_Size"]
    }
    assert AnalysisRequest({"age_at_diagnosis": 99.0}).to_dict()["features"] == {
        "age_at_diagnosis": 99.0
    }


def test_aggregate_outcome_requires_exactly_one_view_or_error() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        PrognosticFeatureAnalysisOutcome(None, None)
    unavailable = PrognosticFeatureAnalysisOutcome(
        None, AggregateAnalysisError("ARTIFACT_UNAVAILABLE", "Unavailable")
    )
    assert unavailable.error.code == "ARTIFACT_UNAVAILABLE"


def test_prognosis_result_requires_finite_value() -> None:
    with pytest.raises(ValueError, match="finite"):
        PrognosisResult(
            _lineage(), "log_partial_hazard", "Model log relative hazard score", math.inf,
            "Model-relative log partial hazard; not an absolute survival probability, mortality probability, risk category, treatment recommendation, or clinical prognosis.",
        )


def test_survival_probability_estimates_require_bounded_monotonic_values() -> None:
    estimates = SurvivalProbabilityEstimates(0.9, 0.8, 0.7)

    assert estimates.survival_probability_1y == 0.9
    assert estimates.survival_probability_3y == 0.8
    assert estimates.survival_probability_5y == 0.7
    assert "internal research estimate" in estimates.interpretation

    with pytest.raises(ValueError, match="bounded"):
        SurvivalProbabilityEstimates(1.1, 0.8, 0.7)

    with pytest.raises(ValueError, match="non-increasing"):
        SurvivalProbabilityEstimates(0.8, 0.9, 0.7)
