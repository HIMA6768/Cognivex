"""R4 framework-independent preprocessing contract tests."""

from __future__ import annotations

import json

import pytest

from src.contracts import (
    CanonicalPreprocessingReport,
    EligibilityReasonCode,
    EligibilityResult,
    ExclusionCount,
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


def test_canonical_report_requires_all_three_task_metadata_contracts() -> None:
    """Dropping a task from the R4 gate would permit incomplete preprocessing readiness."""
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
