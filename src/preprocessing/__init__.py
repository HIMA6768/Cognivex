"""Leak-safe, task-specific METABRIC preprocessing."""

from .eligibility import (
    evaluate_clinical_mutation_survival_eligibility,
    evaluate_clinical_mrna_survival_eligibility,
    evaluate_clinical_survival_eligibility,
    evaluate_subtype_eligibility,
    normalize_subtype_target,
)
from .schema import PreprocessingSchema, load_preprocessing_schema
from .mutations import (
    MutationAnnotationKind,
    MutationBurdenTransformer,
    MutationFrequencySelector,
    classify_mutation_annotation,
)
from .pipelines import (
    assert_safe_feature_names,
    build_clinical_mutation_survival_preprocessor,
    build_clinical_mrna_survival_preprocessor,
    build_clinical_survival_preprocessor,
    build_preprocessing_metadata,
    build_subtype_preprocessor,
    get_transformed_feature_names,
    select_task_features,
)
from .metabric import verify_canonical_preprocessing
from .track_b import (
    SelectedMutationPresenceTransformer,
    build_track_b_preprocessor,
    load_track_b_feature_contract,
    track_b_feature_names,
)
from .track_c import build_track_c_preprocessor, track_c_feature_names

__all__ = [
    "PreprocessingSchema",
    "MutationAnnotationKind",
    "MutationBurdenTransformer",
    "MutationFrequencySelector",
    "assert_safe_feature_names",
    "build_clinical_mrna_survival_preprocessor",
    "build_clinical_mutation_survival_preprocessor",
    "build_clinical_survival_preprocessor",
    "build_preprocessing_metadata",
    "build_subtype_preprocessor",
    "classify_mutation_annotation",
    "evaluate_clinical_mrna_survival_eligibility",
    "evaluate_clinical_mutation_survival_eligibility",
    "evaluate_clinical_survival_eligibility",
    "evaluate_subtype_eligibility",
    "load_preprocessing_schema",
    "get_transformed_feature_names",
    "select_task_features",
    "verify_canonical_preprocessing",
    "normalize_subtype_target",
    "SelectedMutationPresenceTransformer",
    "build_track_b_preprocessor",
    "load_track_b_feature_contract",
    "track_b_feature_names",
    "build_track_c_preprocessor",
    "track_c_feature_names",
]
