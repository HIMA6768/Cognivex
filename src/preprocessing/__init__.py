"""Leak-safe, task-specific METABRIC preprocessing."""

from .eligibility import (
    evaluate_clinical_mrna_survival_eligibility,
    evaluate_clinical_survival_eligibility,
    evaluate_subtype_eligibility,
    normalize_subtype_target,
)
from .schema import PreprocessingSchema, load_preprocessing_schema
from .pipelines import (
    assert_safe_feature_names,
    build_clinical_survival_preprocessor,
    get_transformed_feature_names,
)

__all__ = [
    "PreprocessingSchema",
    "assert_safe_feature_names",
    "build_clinical_survival_preprocessor",
    "evaluate_clinical_mrna_survival_eligibility",
    "evaluate_clinical_survival_eligibility",
    "evaluate_subtype_eligibility",
    "load_preprocessing_schema",
    "get_transformed_feature_names",
    "normalize_subtype_target",
]
