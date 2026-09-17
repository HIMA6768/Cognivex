"""R4 sklearn-compatible task preprocessor tests."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.base import clone

from src.preprocessing.pipelines import (
    assert_safe_feature_names,
    build_clinical_survival_preprocessor,
    get_transformed_feature_names,
)
from src.preprocessing.schema import PreprocessingSchema


@pytest.fixture
def schema() -> PreprocessingSchema:
    return PreprocessingSchema(
        clinical_features=(
            "age_at_diagnosis",
            "tumor_size",
            "tumor_stage",
            "lymph_nodes_examined_positive",
            "er_status_measured_by_ihc",
            "pr_status",
            "her2_status",
        ),
        numeric_clinical_features=("age_at_diagnosis", "tumor_size", "lymph_nodes_examined_positive"),
        categorical_clinical_features=(
            "tumor_stage",
            "er_status_measured_by_ihc",
            "pr_status",
            "her2_status",
        ),
        categorical_categories=(
            ("tumor_stage", ("1", "2", "3", "4", "Unknown")),
            ("er_status_measured_by_ihc", ("Positive", "Negative")),
            ("pr_status", ("Positive", "Negative")),
            ("her2_status", ("Positive", "Negative")),
        ),
        mrna_features=("gene_a", "gene_b"),
        mutation_features=("gene_a_mut",),
        survival_time_column="overall_survival_months",
        survival_event_column="overall_survival",
        subtype_target_column="pam50_+_claudin-low_subtype",
        subtype_classes=("Luminal A", "Luminal B", "Her2", "Basal", "Normal-like", "Claudin-low"),
        subtype_mapping=(("LumA", "Luminal A"),),
    )


@pytest.fixture
def train_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "age_at_diagnosis": [40.0, 50.0, 60.0],
            "tumor_size": [10.0, np.nan, 30.0],
            "tumor_stage": ["1", "Unknown", "3"],
            "lymph_nodes_examined_positive": [0, 2, 4],
            "er_status_measured_by_ihc": ["Positive", np.nan, "Positive"],
            "pr_status": ["Positive", "Negative", "Positive"],
            "her2_status": ["Negative", "Negative", "Positive"],
        }
    )


def test_track_a_uses_train_only_imputation_and_exact_original_missing_indicators(
    schema: PreprocessingSchema,
    train_frame: pd.DataFrame,
) -> None:
    """Global/holdout fitting or post-imputation indicators would change these values."""
    validation = pd.DataFrame(
        {
            "age_at_diagnosis": [70.0],
            "tumor_size": [np.nan],
            "tumor_stage": ["5"],
            "lymph_nodes_examined_positive": [1],
            "er_status_measured_by_ihc": [np.nan],
            "pr_status": ["Positive"],
            "her2_status": ["Negative"],
        }
    )
    pipeline = build_clinical_survival_preprocessor(schema)
    pipeline.fit(train_frame)
    names = get_transformed_feature_names(pipeline)
    state_before = (
        pipeline.named_steps["columns"].named_transformers_["tumor_size"]
        .named_steps["imputer"]
        .statistics_.copy(),
        pipeline.named_steps["columns"].named_transformers_["er_status"]
        .named_steps["imputer"]
        .statistics_.copy(),
    )

    transformed = pipeline.transform(validation)
    state_after = (
        pipeline.named_steps["columns"].named_transformers_["tumor_size"]
        .named_steps["imputer"]
        .statistics_.copy(),
        pipeline.named_steps["columns"].named_transformers_["er_status"]
        .named_steps["imputer"]
        .statistics_.copy(),
    )

    assert names[-2:] == (
        "tumor_size_was_missing",
        "er_status_measured_by_ihc_was_missing",
    )
    assert transformed[0, names.index("tumor_size")] == 20.0
    assert transformed[0, names.index("tumor_size_was_missing")] == 1.0
    assert transformed[0, names.index("er_status_measured_by_ihc_was_missing")] == 1.0
    np.testing.assert_array_equal(state_before[0], [20.0])
    np.testing.assert_array_equal(state_before[1], ["Positive"])
    np.testing.assert_array_equal(state_after[0], state_before[0])
    np.testing.assert_array_equal(state_after[1], state_before[1])


def test_track_a_preserves_numeric_values_and_schema_feature_order(
    schema: PreprocessingSchema,
    train_frame: pd.DataFrame,
) -> None:
    """Accidental shared scaling or unordered categories would break the baseline contract."""
    pipeline = build_clinical_survival_preprocessor(schema)
    transformed = pipeline.fit_transform(train_frame)
    names = get_transformed_feature_names(pipeline)

    assert names == (
        "age_at_diagnosis",
        "tumor_size",
        "lymph_nodes_examined_positive",
        "tumor_stage_1",
        "tumor_stage_2",
        "tumor_stage_3",
        "tumor_stage_4",
        "tumor_stage_Unknown",
        "er_status_measured_by_ihc_Positive",
        "er_status_measured_by_ihc_Negative",
        "pr_status_Positive",
        "pr_status_Negative",
        "her2_status_Positive",
        "her2_status_Negative",
        "tumor_size_was_missing",
        "er_status_measured_by_ihc_was_missing",
    )
    np.testing.assert_array_equal(transformed[0, :3], [40.0, 10.0, 0.0])
    assert transformed[1, names.index("tumor_stage_Unknown")] == 1.0


def test_track_a_is_deterministic_cloneable_and_ignores_unseen_categories(
    schema: PreprocessingSchema,
    train_frame: pd.DataFrame,
) -> None:
    """A non-cloneable or category-learning singleton would be unsafe for future CV."""
    first = build_clinical_survival_preprocessor(schema)
    second = clone(first)
    first_values = first.fit_transform(train_frame)
    second_values = second.fit_transform(train_frame)

    np.testing.assert_array_equal(first_values, second_values)
    assert get_transformed_feature_names(first) == get_transformed_feature_names(second)
    unseen = train_frame.iloc[[0]].assign(tumor_stage="unseen-stage")
    first.transform(unseen)


def test_unapproved_predictor_missingness_fails_clearly(
    schema: PreprocessingSchema,
    train_frame: pd.DataFrame,
) -> None:
    """Silently inventing another imputation policy would hide a schema change."""
    frame = train_frame.copy()
    frame.loc[0, "pr_status"] = np.nan

    with pytest.raises(ValueError, match="pr_status"):
        build_clinical_survival_preprocessor(schema).fit(frame)


@pytest.mark.parametrize(
    "unsafe_name",
    [
        "patient_id",
        "split",
        "overall_survival_months",
        "overall_survival",
        "pam50_+_claudin-low_subtype",
        "survival_eligible",
        "eligibility_reason",
        "tp53_mut",
    ],
)
def test_forbidden_feature_guard_fails_loudly(unsafe_name: str) -> None:
    """Silent post-fit target or metadata dropping would permit leakage upstream."""
    with pytest.raises(ValueError, match="Forbidden predictor"):
        assert_safe_feature_names(("age_at_diagnosis", unsafe_name))
