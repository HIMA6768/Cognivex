"""R4 framework-independent preprocessing contract tests."""

from __future__ import annotations

import json

import pytest

from src.contracts import (
    CanonicalPreprocessingReport,
    EligibilityReasonCode,
    EligibilityResult,
    ExclusionCount,
    MutationFeatureSelection,
    MutationPreprocessingMetadata,
    MutationSelectionMetadata,
    PreprocessingMetadata,
    PreprocessingTask,
    PreprocessingTrack,
    SplitEligibilityCount,
)


def test_eligibility_contract_aggregates_stable_reason_codes() -> None:
    """Removing aggregate audit counts would hide why task rows were excluded."""
    result = EligibilityResult(
        mask=(True, False, False),
        reasons=(
            (),
            (EligibilityReasonCode.NON_POSITIVE_SURVIVAL_DURATION,),
            (
                EligibilityReasonCode.INVALID_SURVIVAL_EVENT,
                EligibilityReasonCode.INVALID_LOCKED_SPLIT,
            ),
        ),
    )

    assert result.eligible_count == 1
    assert result.excluded_count == 2
    assert result.exclusion_counts == (
        ExclusionCount(EligibilityReasonCode.INVALID_LOCKED_SPLIT, 1),
        ExclusionCount(EligibilityReasonCode.INVALID_SURVIVAL_EVENT, 1),
        ExclusionCount(EligibilityReasonCode.NON_POSITIVE_SURVIVAL_DURATION, 1),
    )
    assert result.to_dict()["reasons"][1] == ["NON_POSITIVE_SURVIVAL_DURATION"]


def _mutation_metadata() -> MutationPreprocessingMetadata:
    selection = MutationSelectionMetadata(
        threshold=0.05,
        comparison="greater_than_or_equal",
        fit_row_count=20,
        features=(
            MutationFeatureSelection(
                raw_column="gene_a_mut",
                gene="gene_a",
                derived_feature_name="gene_a_mut_present",
                prevalence=0.05,
                retained=True,
            ),
            MutationFeatureSelection(
                raw_column="gene_b_mut",
                gene="gene_b",
                derived_feature_name="gene_b_mut_present",
                prevalence=0.0,
                retained=False,
            ),
        ),
    )
    return MutationPreprocessingMetadata(
        representation_policy="zero absent; nonzero annotation present",
        source_feature_names=("gene_a_mut", "gene_b_mut"),
        selection=selection,
        burden_source_feature_count=2,
        burden_feature_name="mutation_burden_log1p",
        burden_transformation="log1p of presence count across all source genes",
    )


def test_track_d_mutation_metadata_serializes_fit_evidence_and_scaling_groups() -> None:
    """Dropping fitted selection or scale-group evidence would make Track D unauditable."""
    metadata = PreprocessingMetadata(
        task=PreprocessingTask.CLINICAL_MUTATION_SURVIVAL,
        track=PreprocessingTrack.TRACK_D,
        source_dataset="METABRIC",
        source_version="Version 1",
        fitted_on_split="train",
        eligible_row_count=20,
        excluded_row_count=0,
        exclusion_counts=(),
        raw_feature_count=9,
        transformed_feature_count=3,
        clinical_feature_names=("age_at_diagnosis",),
        mrna_feature_names=(),
        final_feature_names=(
            "age_at_diagnosis",
            "gene_a_mut_present",
            "mutation_burden_log1p",
        ),
        imputation_strategy="training-only clinical imputation",
        missing_indicator_strategy="original-value indicators",
        categorical_encoding_strategy="schema categories",
        scaling_strategy="continuous only",
        mutation_policy="fit-local binary selector and all-gene burden",
        nc_policy="NC does not affect Track D",
        zero_duration_policy="excluded from survival tasks",
        forbidden_feature_guard_passed=True,
        mutation_metadata=_mutation_metadata(),
        standardized_continuous_feature_names=(
            "age_at_diagnosis",
            "mutation_burden_log1p",
        ),
        unscaled_binary_feature_names=("gene_a_mut_present",),
    )

    decoded = metadata.to_dict()

    assert decoded["task"] == "clinical_mutation_survival"
    assert decoded["track"] == "Track D"
    assert decoded["mutation_metadata"]["selection"]["threshold"] == 0.05
    assert decoded["mutation_metadata"]["selection"]["retained_genes"] == ["gene_a"]
    assert decoded["mutation_metadata"]["selection"]["excluded_genes"] == ["gene_b"]
    assert decoded["mutation_metadata"]["selection"]["retained_feature_names"] == [
        "gene_a_mut_present"
    ]
    assert decoded["standardized_continuous_feature_names"] == [
        "age_at_diagnosis",
        "mutation_burden_log1p",
    ]
    assert decoded["unscaled_binary_feature_names"] == ["gene_a_mut_present"]


@pytest.mark.parametrize(
    ("standardized", "unscaled"),
    [
        (("age_at_diagnosis",), ("gene_a_mut_present",)),
        (
            ("age_at_diagnosis", "mutation_burden_log1p"),
            ("age_at_diagnosis", "gene_a_mut_present"),
        ),
    ],
)
def test_track_d_metadata_requires_an_exact_disjoint_final_feature_partition(
    standardized: tuple[str, ...], unscaled: tuple[str, ...]
) -> None:
    """Missing or overlapping scaling classifications would misstate fitted preprocessing."""
    with pytest.raises(ValueError, match="partition"):
        PreprocessingMetadata(
            task=PreprocessingTask.CLINICAL_MUTATION_SURVIVAL,
            track=PreprocessingTrack.TRACK_D,
            source_dataset="METABRIC",
            source_version="Version 1",
            fitted_on_split="train",
            eligible_row_count=20,
            excluded_row_count=0,
            exclusion_counts=(),
            raw_feature_count=9,
            transformed_feature_count=3,
            clinical_feature_names=("age_at_diagnosis",),
            mrna_feature_names=(),
            final_feature_names=(
                "age_at_diagnosis",
                "gene_a_mut_present",
                "mutation_burden_log1p",
            ),
            imputation_strategy="training-only clinical imputation",
            missing_indicator_strategy="original-value indicators",
            categorical_encoding_strategy="schema categories",
            scaling_strategy="continuous only",
            mutation_policy="fit-local binary selector and all-gene burden",
            nc_policy="NC does not affect Track D",
            zero_duration_policy="excluded from survival tasks",
            forbidden_feature_guard_passed=True,
            mutation_metadata=_mutation_metadata(),
            standardized_continuous_feature_names=standardized,
            unscaled_binary_feature_names=unscaled,
        )


def test_preprocessing_metadata_serializes_without_patient_identifiers() -> None:
    """Adding row-level identifiers to public R4 metadata would violate its audit boundary."""
    metadata = PreprocessingMetadata(
        task=PreprocessingTask.CLINICAL_SURVIVAL,
        track=PreprocessingTrack.TRACK_A,
        source_dataset="METABRIC",
        source_version="Version 1",
        fitted_on_split="train",
        eligible_row_count=1903,
        excluded_row_count=1,
        exclusion_counts=(
            ExclusionCount(EligibilityReasonCode.NON_POSITIVE_SURVIVAL_DURATION, 1),
        ),
        raw_feature_count=2,
        transformed_feature_count=2,
        clinical_feature_names=("age_at_diagnosis", "tumor_size"),
        mrna_feature_names=(),
        final_feature_names=("age_at_diagnosis", "tumor_size_was_missing"),
        imputation_strategy="training-only median and most-frequent imputation",
        missing_indicator_strategy="original pre-imputation nullness",
        categorical_encoding_strategy="schema categories with unknown values ignored",
        scaling_strategy="no numeric scaling",
        mutation_policy="excluded",
        nc_policy="allowed when survival targets are valid",
        zero_duration_policy="excluded from survival tasks",
        forbidden_feature_guard_passed=True,
    )

    decoded = json.loads(json.dumps(metadata.to_dict()))

    assert decoded["task"] == "clinical_survival"
    assert decoded["track"] == "Track A"
    assert decoded["exclusion_counts"] == [
        {"reason": "NON_POSITIVE_SURVIVAL_DURATION", "count": 1}
    ]
    assert "patient_id" not in str(decoded)


def test_canonical_report_requires_all_four_task_metadata_contracts() -> None:
    """Dropping a task from the R4D gate would permit incomplete preprocessing readiness."""
    common = dict(
        source_dataset="METABRIC",
        source_version="Version 1",
        fitted_on_split="train",
        eligible_row_count=1,
        excluded_row_count=0,
        exclusion_counts=(),
        raw_feature_count=1,
        transformed_feature_count=1,
        final_feature_names=("gene_a",),
        imputation_strategy="none",
        missing_indicator_strategy="none",
        categorical_encoding_strategy="none",
        mutation_policy="excluded",
        forbidden_feature_guard_passed=True,
    )
    tasks = (
        PreprocessingMetadata(
            task=PreprocessingTask.CLINICAL_SURVIVAL,
            track=PreprocessingTrack.TRACK_A,
            clinical_feature_names=("gene_a",),
            mrna_feature_names=(),
            scaling_strategy="no scaling",
            nc_policy="allowed",
            zero_duration_policy="excluded",
            split_counts=(SplitEligibilityCount("train", 1, 0),),
            **common,
        ),
        PreprocessingMetadata(
            task=PreprocessingTask.CLINICAL_MRNA_SURVIVAL,
            track=PreprocessingTrack.TRACK_B,
            clinical_feature_names=(),
            mrna_feature_names=("gene_a",),
            scaling_strategy="training-only scaling",
            nc_policy="allowed",
            zero_duration_policy="excluded",
            split_counts=(SplitEligibilityCount("train", 1, 0),),
            **common,
        ),
        PreprocessingMetadata(
            task=PreprocessingTask.SUBTYPE_CLASSIFICATION,
            track=PreprocessingTrack.TRACK_C,
            clinical_feature_names=(),
            mrna_feature_names=("gene_a",),
            scaling_strategy="canonical Z-scores retained",
            nc_policy="excluded",
            zero_duration_policy="not applicable",
            split_counts=(SplitEligibilityCount("train", 1, 0),),
            **common,
        ),
        PreprocessingMetadata(
            task=PreprocessingTask.CLINICAL_MUTATION_SURVIVAL,
            track=PreprocessingTrack.TRACK_D,
            source_dataset="METABRIC",
            source_version="Version 1",
            fitted_on_split="train",
            eligible_row_count=1,
            excluded_row_count=0,
            exclusion_counts=(),
            raw_feature_count=3,
            transformed_feature_count=3,
            clinical_feature_names=("age_at_diagnosis",),
            mrna_feature_names=(),
            final_feature_names=(
                "age_at_diagnosis",
                "gene_a_mut_present",
                "mutation_burden_log1p",
            ),
            imputation_strategy="training-only clinical imputation",
            missing_indicator_strategy="original-value indicators",
            categorical_encoding_strategy="schema categories",
            scaling_strategy="continuous only",
            mutation_policy="fit-local binary selector and all-gene burden",
            nc_policy="allowed",
            zero_duration_policy="excluded",
            forbidden_feature_guard_passed=True,
            split_counts=(SplitEligibilityCount("train", 1, 0),),
            mutation_metadata=_mutation_metadata(),
            standardized_continuous_feature_names=(
                "age_at_diagnosis",
                "mutation_burden_log1p",
            ),
            unscaled_binary_feature_names=("gene_a_mut_present",),
        ),
    )

    report = CanonicalPreprocessingReport(
        tasks=tasks,
        tumor_size_missing_indicator_count=20,
        er_ihc_missing_indicator_count=30,
        mutation_feature_count=0,
        forbidden_feature_count=0,
        train_only_fit_verified=True,
        raw_sha256="a" * 64,
        prepared_sha256="b" * 64,
        canonical_artifacts_unchanged=True,
    )

    assert [task["task"] for task in report.to_dict()["tasks"]] == [
        "clinical_survival",
        "clinical_mrna_survival",
        "subtype_classification",
        "clinical_mutation_survival",
    ]


@pytest.mark.parametrize(
    "factory",
    [
        lambda: EligibilityResult(mask=(True,), reasons=()),
        lambda: EligibilityResult(mask=(False,), reasons=((),)),
        lambda: ExclusionCount(EligibilityReasonCode.NC_SUBTYPE, -1),
        lambda: PreprocessingMetadata(
            task=PreprocessingTask.CLINICAL_SURVIVAL,
            track=PreprocessingTrack.TRACK_A,
            source_dataset="METABRIC",
            source_version="Version 1",
            fitted_on_split="validation",
            eligible_row_count=1,
            excluded_row_count=0,
            exclusion_counts=(),
            raw_feature_count=1,
            transformed_feature_count=1,
            clinical_feature_names=("age_at_diagnosis",),
            mrna_feature_names=(),
            final_feature_names=("age_at_diagnosis",),
            imputation_strategy="none",
            missing_indicator_strategy="none",
            categorical_encoding_strategy="none",
            scaling_strategy="none",
            mutation_policy="excluded",
            nc_policy="allowed",
            zero_duration_policy="excluded",
            forbidden_feature_guard_passed=True,
        ),
    ],
)
def test_invalid_preprocessing_contract_values_are_rejected(factory) -> None:
    """Relaxed validation would allow misleading or leakage-prone metadata."""
    with pytest.raises((TypeError, ValueError)):
        factory()
