"""Framework-independent R5 survival contract tests."""

from __future__ import annotations

import pytest

from src.contracts import (
    CategoricalFeatureComparison,
    ConcordanceResult,
    CoxModelConfiguration,
    SurvivalCohortSummary,
)
from tests.r5_helpers import make_track_a_result


def test_track_a_result_serializes_nested_evidence() -> None:
    payload = make_track_a_result().to_dict()

    assert payload["configuration"]["track"] == "track_a"
    assert payload["configuration"]["categorical_comparisons"] == [
        {
            "raw_variable": "tumor_stage",
            "category": "2",
            "reference_category": "1",
            "derived_feature_name": "tumor_stage_2",
        }
    ]
    assert payload["matrix_diagnostic"]["condition_number"] == 1.0
    assert payload["validation_metric"]["score_direction"] == "higher_risk_is_higher_hazard"
    assert payload["ph_diagnostics"]["status"] == "PASSED"
    assert payload["test_transformed"] is False


def test_concordance_rejects_out_of_range_value() -> None:
    with pytest.raises(ValueError, match="c_index"):
        ConcordanceResult(
            "harrell_c_index",
            "validation",
            3,
            2,
            1,
            1.01,
            "log_partial_hazard",
            "higher_risk_is_higher_hazard",
            True,
            "a" * 64,
        )


def test_cohort_summary_requires_events_and_censoring_to_sum_to_count() -> None:
    with pytest.raises(ValueError, match="event and censored"):
        SurvivalCohortSummary("train", 3, 3, 1, "a" * 64)


def test_model_configuration_requires_unique_ordered_features() -> None:
    with pytest.raises(ValueError, match="feature_names"):
        CoxModelConfiguration(
            track="track_a",
            task="clinical_survival",
            model_type="CoxPHFitter",
            baseline_estimation_method="breslow",
            penalizer=0.0,
            l1_ratio=0.0,
            strata=(),
            alpha=0.05,
            duration_column="overall_survival_months",
            event_column="overall_survival",
            feature_names=("age", "age"),
            categorical_comparisons=(),
        )


def test_categorical_comparison_requires_distinct_category_and_reference() -> None:
    with pytest.raises(ValueError, match="must differ"):
        CategoricalFeatureComparison(
            raw_variable="tumor_stage",
            category="1",
            reference_category="1",
            derived_feature_name="tumor_stage_1",
        )
