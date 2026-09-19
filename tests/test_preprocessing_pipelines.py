"""R4 sklearn-compatible task preprocessor tests."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.base import clone

from src.preprocessing.pipelines import (
    assert_safe_feature_names,
    build_clinical_mutation_survival_preprocessor,
    build_clinical_mrna_survival_preprocessor,
    build_clinical_survival_preprocessor,
    build_preprocessing_metadata,
    build_subtype_preprocessor,
    get_transformed_feature_names,
    select_task_features,
)
from src.contracts import EligibilityResult, PreprocessingTask, SplitEligibilityCount
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
        "tumor_stage_2",
        "tumor_stage_3",
        "tumor_stage_4",
        "tumor_stage_Unknown",
        "er_status_measured_by_ihc_Positive",
        "pr_status_Positive",
        "her2_status_Positive",
        "tumor_size_was_missing",
        "er_status_measured_by_ihc_was_missing",
    )
    assert not {
        "tumor_stage_1",
        "er_status_measured_by_ihc_Negative",
        "pr_status_Negative",
        "her2_status_Negative",
    }.intersection(names)
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


def test_track_b_scales_only_with_training_statistics_and_preserves_gene_order(
    schema: PreprocessingSchema,
    train_frame: pd.DataFrame,
) -> None:
    """Fitting the scaler on holdout values or reordering genes would leak and change Coxnet input."""
    train = train_frame.assign(gene_a=[0.0, 2.0, 4.0], gene_b=[10.0, 20.0, 30.0])
    validation = train.iloc[[0]].assign(gene_a=1000.0, gene_b=-1000.0)
    pipeline = build_clinical_mrna_survival_preprocessor(schema)
    pipeline.fit(train)
    names = get_transformed_feature_names(pipeline)
    scaler = pipeline.named_steps["columns"].named_transformers_["mrna"]
    mean_before = scaler.mean_.copy()

    pipeline.transform(validation)

    np.testing.assert_array_equal(mean_before, [2.0, 20.0])
    np.testing.assert_array_equal(scaler.mean_, mean_before)
    assert names[-2:] == ("gene_a", "gene_b")
    assert len(names) == 18
    assert {
        "tumor_stage_1",
        "er_status_measured_by_ihc_Negative",
        "pr_status_Negative",
        "her2_status_Negative",
    }.issubset(names)


def test_track_c_preserves_canonical_z_scores_without_target_or_scaler(
    schema: PreprocessingSchema,
) -> None:
    """Adding R4 scaling or subtype target data would violate the approved Track C boundary."""
    full = pd.DataFrame(
        {
            "gene_a": [0.25, -0.5],
            "gene_b": [1.5, 2.0],
            "pam50_+_claudin-low_subtype": ["LumA", "Basal"],
            "gene_a_mut": ["0", "H1047R"],
        }
    )
    selected = select_task_features(full, PreprocessingTask.SUBTYPE_CLASSIFICATION, schema)
    pipeline = build_subtype_preprocessor(schema)
    transformed = pipeline.fit_transform(selected)

    assert tuple(selected.columns) == ("gene_a", "gene_b")
    assert get_transformed_feature_names(pipeline) == ("gene_a", "gene_b")
    np.testing.assert_array_equal(transformed, [[0.25, 1.5], [-0.5, 2.0]])
    assert not any("scaler" in name for name in pipeline.named_steps)


def test_track_d_factory_scales_only_continuous_features_and_preserves_binary_outputs(
    schema: PreprocessingSchema,
    train_frame: pd.DataFrame,
) -> None:
    """Scaling binary indicators or leaving continuous Track D inputs unscaled breaks its Cox contract."""
    frame = train_frame.assign(gene_a_mut=["0", "H1047R", "0"])
    pipeline = build_clinical_mutation_survival_preprocessor(schema)
    transformed = pipeline.fit_transform(frame)
    names = get_transformed_feature_names(pipeline)

    assert names[:16] == (
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
    assert names[-2:] == ("gene_a_mut_present", "mutation_burden_log1p")
    for feature in (
        "age_at_diagnosis",
        "tumor_size",
        "lymph_nodes_examined_positive",
        "mutation_burden_log1p",
    ):
        assert transformed[:, names.index(feature)].mean() == pytest.approx(0.0, abs=1e-12)
    for feature in names[3:16] + ("gene_a_mut_present",):
        assert set(transformed[:, names.index(feature)]) <= {0.0, 1.0}


def test_track_d_metadata_explicitly_partitions_standardized_and_unscaled_features(
    schema: PreprocessingSchema,
    train_frame: pd.DataFrame,
) -> None:
    """Implicit scaling knowledge would make fitted Track D outputs impossible to audit."""
    frame = train_frame.assign(gene_a_mut=["0", "H1047R", "0"])
    pipeline = build_clinical_mutation_survival_preprocessor(schema).fit(frame)
    metadata = build_preprocessing_metadata(
        task=PreprocessingTask.CLINICAL_MUTATION_SURVIVAL,
        schema=schema,
        eligibility=EligibilityResult(mask=(True, True, True), reasons=((), (), ())),
        fitted_preprocessor=pipeline,
        split_counts=(SplitEligibilityCount("train", 3, 0),),
        source_dataset="METABRIC",
        source_version="Version 1",
    )

    assert metadata.standardized_continuous_feature_names == (
        "age_at_diagnosis",
        "tumor_size",
        "lymph_nodes_examined_positive",
        "mutation_burden_log1p",
    )
    assert set(metadata.standardized_continuous_feature_names).isdisjoint(
        metadata.unscaled_binary_feature_names
    )
    assert set(metadata.standardized_continuous_feature_names + metadata.unscaled_binary_feature_names) == set(
        metadata.final_feature_names
    )
    assert metadata.mutation_metadata is not None
    assert metadata.mutation_metadata.source_feature_names == ("gene_a_mut",)
    assert metadata.mutation_metadata.selection.fit_row_count == 3
    assert metadata.mutation_metadata.selection.retained_feature_names == ("gene_a_mut_present",)
    assert metadata.mutation_metadata.burden_source_feature_count == 1


def test_task_feature_selection_excludes_targets_ids_splits_and_mutations(
    schema: PreprocessingSchema,
    train_frame: pd.DataFrame,
) -> None:
    """Selecting from the full canonical frame must never pass forbidden fields downstream."""
    full = train_frame.assign(
        patient_id=["P1", "P2", "P3"],
        split=["train", "train", "train"],
        overall_survival_months=[1.0, 2.0, 3.0],
        overall_survival=[1, 0, 1],
        **{
            "pam50_+_claudin-low_subtype": ["LumA", "LumB", "Basal"],
            "gene_a": [0.0, 1.0, 2.0],
            "gene_b": [2.0, 1.0, 0.0],
            "gene_a_mut": ["0", "H1047R", "0"],
        },
    )

    assert tuple(select_task_features(full, PreprocessingTask.CLINICAL_SURVIVAL, schema).columns) == (
        schema.clinical_features
    )
    assert tuple(select_task_features(full, PreprocessingTask.CLINICAL_MRNA_SURVIVAL, schema).columns) == (
        schema.clinical_features + schema.mrna_features
    )
    assert tuple(select_task_features(full, PreprocessingTask.SUBTYPE_CLASSIFICATION, schema).columns) == (
        schema.mrna_features
    )
    assert tuple(
        select_task_features(full, PreprocessingTask.CLINICAL_MUTATION_SURVIVAL, schema).columns
    ) == (schema.clinical_features + schema.mutation_features)


def test_genomic_factories_are_fresh_cloneable_and_deterministic(
    schema: PreprocessingSchema,
    train_frame: pd.DataFrame,
) -> None:
    """Shared fitted singleton state would leak across folds and application reruns."""
    track_b_frame = train_frame.assign(gene_a=[0.0, 1.0, 2.0], gene_b=[2.0, 1.0, 0.0])
    for factory, frame in (
        (build_clinical_mrna_survival_preprocessor, track_b_frame),
        (build_subtype_preprocessor, track_b_frame.loc[:, ["gene_a", "gene_b"]]),
        (
            build_clinical_mutation_survival_preprocessor,
            train_frame.assign(gene_a_mut=["0", "H1047R", "0"]),
        ),
    ):
        first = factory(schema)
        second = clone(first)
        np.testing.assert_array_equal(first.fit_transform(frame), second.fit_transform(frame))
        assert get_transformed_feature_names(first) == get_transformed_feature_names(second)


def test_track_b_remains_mutation_free_after_track_d_is_added(
    schema: PreprocessingSchema,
    train_frame: pd.DataFrame,
) -> None:
    """Sharing genomic branches could accidentally add Track D mutation features to Track B."""
    full = train_frame.assign(
        gene_a=[0.0, 1.0, 2.0],
        gene_b=[2.0, 1.0, 0.0],
        gene_a_mut=["0", "H1047R", "0"],
    )
    selected = select_task_features(full, PreprocessingTask.CLINICAL_MRNA_SURVIVAL, schema)
    names = get_transformed_feature_names(
        build_clinical_mrna_survival_preprocessor(schema).fit(selected)
    )

    assert "gene_a_mut" not in selected
    assert not any(name.endswith("_mut_present") for name in names)
