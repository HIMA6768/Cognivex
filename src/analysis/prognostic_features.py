"""Explicit frozen R6 genomic feature mapping for R8 analysis."""

from __future__ import annotations

from typing import Mapping

from src.artifacts.prognostic_features import VerifiedTrackBSource
from src.contracts import FeatureType, GenomicFeatureMapping
from src.preprocessing.track_b import track_b_feature_names


R6_CLINICAL_MODEL_FEATURES = (
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


def _ordered_unique_names(contract: Mapping[str, object], key: str, expected: int) -> tuple[str, ...]:
    values = contract.get(key)
    if not isinstance(values, (list, tuple)) or len(values) != expected:
        label = "expression" if key == "expression_features" else "mutation"
        raise ValueError(f"R8 requires exactly {expected} {label} features")
    names = tuple(values)
    if any(not isinstance(name, str) or not name.strip() for name in names):
        raise ValueError(f"{key} must contain non-empty names")
    if len(names) != len(set(names)):
        raise ValueError(f"{key} must contain unique names")
    return names


def build_genomic_feature_mapping(
    feature_contract: Mapping[str, object],
    model_feature_names: tuple[str, ...],
) -> tuple[GenomicFeatureMapping, ...]:
    """Map only the explicit R6 expression and mutation contract in frozen order."""
    expression_names = _ordered_unique_names(feature_contract, "expression_features", 50)
    mutation_names = _ordered_unique_names(feature_contract, "mutation_features", 18)
    if set(expression_names) & set(mutation_names):
        raise ValueError("expression and mutation feature groups must be disjoint")
    if len(model_feature_names) != 80:
        raise ValueError("R6 fitted model must contain exactly 80 names")
    if len(model_feature_names) != len(set(model_feature_names)):
        raise ValueError("R6 fitted model names must be unique")
    expression = tuple(
        GenomicFeatureMapping(i, raw, raw, FeatureType.EXPRESSION)
        for i, raw in enumerate(expression_names, start=1)
    )
    mutation = tuple(
        GenomicFeatureMapping(i, raw, f"{raw}_present", FeatureType.MUTATION_PRESENCE)
        for i, raw in enumerate(mutation_names, start=51)
    )
    mapping = expression + mutation
    mapped_names = tuple(item.model_feature_name for item in mapping)
    if model_feature_names[:12] != R6_CLINICAL_MODEL_FEATURES:
        raise ValueError("R6 clinical encoded prefix is not the frozen 12-feature authority")
    if model_feature_names[12:] != mapped_names:
        raise ValueError("R6 fitted names do not match the explicit mapped genomic order")
    return mapping


def validate_genomic_mapping_authorities(
    mapping: tuple[GenomicFeatureMapping, ...],
    source: VerifiedTrackBSource,
) -> None:
    """Require persisted, preprocessor, adapter, params, and summary orders to agree."""
    expected_mapping = build_genomic_feature_mapping(source.feature_contract, source.model_feature_names)
    if mapping != expected_mapping:
        raise ValueError("genomic mapping differs from the persisted feature-contract authority")
    expected = R6_CLINICAL_MODEL_FEATURES + tuple(item.model_feature_name for item in mapping)
    authorities = {
        "persisted": source.model_feature_names,
        "preprocessor": track_b_feature_names(source.preprocessor),
        "adapter": tuple(source.model.feature_names),
        "params": tuple(source.model.fitter.params_.index),
        "summary": tuple(source.model.fitter.summary.index),
    }
    mismatches = [name for name, values in authorities.items() if tuple(values) != expected]
    if mismatches:
        raise ValueError(f"R6 fitted feature-order authority mismatch: {', '.join(mismatches)}")
