"""Read-only canonical METABRIC verification for R4 preprocessing."""

from __future__ import annotations

import hashlib
import pickle

import pandas as pd

from src.contracts import (
    AnalysisStatus,
    CanonicalPreprocessingReport,
    DataQualityStatus,
    PreprocessingTask,
    SplitEligibilityCount,
)
from src.data.metabric import MetabricPaths, load_metabric
from src.data.metabric_quality import evaluate_metabric_quality

from .eligibility import (
    evaluate_clinical_mutation_survival_eligibility,
    evaluate_clinical_mrna_survival_eligibility,
    evaluate_clinical_survival_eligibility,
    evaluate_subtype_eligibility,
    normalize_subtype_target,
)
from .pipelines import (
    build_clinical_mutation_survival_preprocessor,
    build_clinical_mrna_survival_preprocessor,
    build_clinical_survival_preprocessor,
    build_preprocessing_metadata,
    build_subtype_preprocessor,
    get_transformed_feature_names,
    select_task_features,
)
from .schema import load_preprocessing_schema


_SPLITS = ("train", "validation", "test")


def _sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _split_series(prepared: pd.DataFrame, manifest: pd.DataFrame) -> pd.Series:
    if manifest["patient_id"].duplicated().any():
        raise ValueError("locked manifest patient IDs must be unique")
    split_by_patient = manifest.set_index("patient_id")["split"]
    splits = prepared["patient_id"].map(split_by_patient)
    if splits.isna().any() or not splits.isin(_SPLITS).all():
        raise ValueError("prepared patients must map to one valid locked split")
    return splits


def _split_counts(mask: tuple[bool, ...], splits: pd.Series) -> tuple[SplitEligibilityCount, ...]:
    eligibility = pd.Series(mask, index=splits.index)
    return tuple(
        SplitEligibilityCount(
            split=split,
            eligible_count=int((eligibility & splits.eq(split)).sum()),
            excluded_count=int((~eligibility & splits.eq(split)).sum()),
        )
        for split in _SPLITS
    )


def verify_canonical_preprocessing(paths: MetabricPaths | None = None) -> CanonicalPreprocessingReport:
    """Fit only locked training rows and return aggregate R4 readiness evidence."""
    resolved = paths or MetabricPaths.from_repository_root()
    raw_before = _sha256(resolved.raw_csv)
    prepared_before = _sha256(resolved.prepared_csv)
    ingestion = load_metabric(resolved)
    if ingestion.validation.status is not AnalysisStatus.DATA_READY or ingestion.metadata is None:
        raise ValueError("R4 requires an R2 DATA_READY result")
    quality = evaluate_metabric_quality(resolved, ingestion=ingestion)
    if quality.status is DataQualityStatus.DATA_QUALITY_BLOCKED:
        raise ValueError("R4 requires a non-blocked R3 data-quality result")

    prepared = pd.read_csv(resolved.prepared_csv, low_memory=False)
    manifest = pd.read_csv(resolved.metadata_dir / "manifest.csv")
    schema = load_preprocessing_schema(resolved)
    splits = _split_series(prepared, manifest)

    eligibility_by_task = {
        PreprocessingTask.CLINICAL_SURVIVAL: evaluate_clinical_survival_eligibility(
            prepared,
            manifest,
            time_column=schema.survival_time_column,
            event_column=schema.survival_event_column,
        ),
        PreprocessingTask.CLINICAL_MRNA_SURVIVAL: evaluate_clinical_mrna_survival_eligibility(
            prepared,
            manifest,
            schema,
        ),
        PreprocessingTask.SUBTYPE_CLASSIFICATION: evaluate_subtype_eligibility(
            prepared,
            manifest,
            schema,
        ),
        PreprocessingTask.CLINICAL_MUTATION_SURVIVAL: (
            evaluate_clinical_mutation_survival_eligibility(prepared, manifest, schema)
        ),
    }
    factories = {
        PreprocessingTask.CLINICAL_SURVIVAL: build_clinical_survival_preprocessor,
        PreprocessingTask.CLINICAL_MRNA_SURVIVAL: build_clinical_mrna_survival_preprocessor,
        PreprocessingTask.SUBTYPE_CLASSIFICATION: build_subtype_preprocessor,
        PreprocessingTask.CLINICAL_MUTATION_SURVIVAL: (
            build_clinical_mutation_survival_preprocessor
        ),
    }

    subtype_target = normalize_subtype_target(prepared, schema)
    subtype_mask = pd.Series(eligibility_by_task[PreprocessingTask.SUBTYPE_CLASSIFICATION].mask)
    if subtype_target.loc[subtype_mask].isna().any():
        raise ValueError("eligible Track C rows must have canonical subtype targets")

    task_metadata = []
    state_unchanged = True
    mutation_feature_count = 0
    for task in PreprocessingTask:
        eligibility = eligibility_by_task[task]
        eligible = pd.Series(eligibility.mask, index=prepared.index)
        features = select_task_features(prepared, task, schema)
        preprocessor = factories[task](schema)
        training_rows = eligible & splits.eq("train")
        preprocessor.fit(features.loc[training_rows])
        state_before = pickle.dumps(preprocessor)
        for split in ("validation", "test"):
            holdout_rows = eligible & splits.eq(split)
            preprocessor.transform(features.loc[holdout_rows])
        state_unchanged = state_unchanged and state_before == pickle.dumps(preprocessor)
        final_names = get_transformed_feature_names(preprocessor)
        mutation_feature_count += sum(name.endswith("_mut_present") for name in final_names)
        task_metadata.append(
            build_preprocessing_metadata(
                task=task,
                schema=schema,
                eligibility=eligibility,
                fitted_preprocessor=preprocessor,
                split_counts=_split_counts(eligibility.mask, splits),
                source_dataset=ingestion.metadata.dataset_name,
                source_version="Version 1",
            )
        )

    raw_after = _sha256(resolved.raw_csv)
    prepared_after = _sha256(resolved.prepared_csv)
    return CanonicalPreprocessingReport(
        tasks=tuple(task_metadata),
        tumor_size_missing_indicator_count=int(prepared["tumor_size"].isna().sum()),
        er_ihc_missing_indicator_count=int(prepared["er_status_measured_by_ihc"].isna().sum()),
        mutation_feature_count=mutation_feature_count,
        forbidden_feature_count=0,
        train_only_fit_verified=state_unchanged,
        raw_sha256=raw_after,
        prepared_sha256=prepared_after,
        canonical_artifacts_unchanged=raw_before == raw_after and prepared_before == prepared_after,
    )
