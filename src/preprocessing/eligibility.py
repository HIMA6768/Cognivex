"""Task-specific, patient-aligned R4 eligibility rules."""

from __future__ import annotations

import math

import pandas as pd

from src.contracts import EligibilityReasonCode, EligibilityResult

from .schema import PreprocessingSchema


_ALLOWED_SPLITS = frozenset({"train", "validation", "test"})


def _required_columns(frame: pd.DataFrame, names: tuple[str, ...], subject: str) -> None:
    missing = tuple(name for name in names if name not in frame.columns)
    if missing:
        raise ValueError(f"{subject} is missing required columns: {', '.join(missing)}")


def _aligned_splits(prepared: pd.DataFrame, manifest: pd.DataFrame) -> pd.Series:
    _required_columns(prepared, ("patient_id",), "prepared data")
    _required_columns(manifest, ("patient_id", "split"), "manifest")
    if prepared["patient_id"].isna().any() or prepared["patient_id"].duplicated().any():
        raise ValueError("prepared patient_id values must be present and unique")
    if manifest["patient_id"].isna().any() or manifest["patient_id"].duplicated().any():
        raise ValueError("manifest patient_id values must be present and unique")
    split_by_patient = manifest.set_index("patient_id")["split"]
    return prepared["patient_id"].map(split_by_patient)


def _is_missing(value: object) -> bool:
    return bool(pd.isna(value)) or isinstance(value, str) and not value.strip()


def _survival_reasons(
    row: pd.Series,
    split: object,
    time_column: str,
    event_column: str,
) -> tuple[EligibilityReasonCode, ...]:
    reasons: list[EligibilityReasonCode] = []
    time_value = row[time_column]
    if _is_missing(time_value):
        reasons.append(EligibilityReasonCode.MISSING_SURVIVAL_DURATION)
    else:
        try:
            numeric_time = float(time_value)
        except (TypeError, ValueError):
            reasons.append(EligibilityReasonCode.NON_NUMERIC_SURVIVAL_DURATION)
        else:
            if not math.isfinite(numeric_time):
                reasons.append(EligibilityReasonCode.NON_FINITE_SURVIVAL_DURATION)
            elif numeric_time <= 0:
                reasons.append(EligibilityReasonCode.NON_POSITIVE_SURVIVAL_DURATION)

    event_value = row[event_column]
    if _is_missing(event_value):
        reasons.append(EligibilityReasonCode.MISSING_SURVIVAL_EVENT)
    else:
        try:
            numeric_event = float(event_value)
        except (TypeError, ValueError):
            reasons.append(EligibilityReasonCode.INVALID_SURVIVAL_EVENT)
        else:
            if not math.isfinite(numeric_event) or numeric_event not in {0.0, 1.0}:
                reasons.append(EligibilityReasonCode.INVALID_SURVIVAL_EVENT)

    if split not in _ALLOWED_SPLITS:
        reasons.append(EligibilityReasonCode.INVALID_LOCKED_SPLIT)
    return tuple(reasons)


def _mrna_reasons(row: pd.Series, features: tuple[str, ...]) -> tuple[EligibilityReasonCode, ...]:
    values = row.loc[list(features)]
    missing_mask = values.map(_is_missing)
    numeric = pd.to_numeric(values, errors="coerce")
    reasons: list[EligibilityReasonCode] = []
    if bool(missing_mask.any()):
        reasons.append(EligibilityReasonCode.MISSING_MRNA_VALUE)
    if bool((numeric.isna() & ~missing_mask).any()):
        reasons.append(EligibilityReasonCode.NON_NUMERIC_MRNA_VALUE)
    if any(not math.isfinite(float(value)) for value in numeric.dropna()):
        reasons.append(EligibilityReasonCode.NON_FINITE_MRNA_VALUE)
    return tuple(reasons)


def evaluate_clinical_survival_eligibility(
    prepared: pd.DataFrame,
    manifest: pd.DataFrame,
    *,
    time_column: str = "overall_survival_months",
    event_column: str = "overall_survival",
) -> EligibilityResult:
    """Return Track A eligibility without consulting subtype or predictor nullness."""
    _required_columns(prepared, (time_column, event_column), "prepared data")
    splits = _aligned_splits(prepared, manifest)
    reasons = tuple(
        _survival_reasons(row, split, time_column, event_column)
        for (_, row), split in zip(prepared.iterrows(), splits, strict=True)
    )
    return EligibilityResult(mask=tuple(not row_reasons for row_reasons in reasons), reasons=reasons)


def evaluate_clinical_mrna_survival_eligibility(
    prepared: pd.DataFrame,
    manifest: pd.DataFrame,
    schema: PreprocessingSchema,
) -> EligibilityResult:
    """Return Track B eligibility from survival validity plus mRNA integrity."""
    _required_columns(prepared, schema.mrna_features, "prepared mRNA data")
    survival = evaluate_clinical_survival_eligibility(
        prepared,
        manifest,
        time_column=schema.survival_time_column,
        event_column=schema.survival_event_column,
    )
    reasons = tuple(
        row_reasons + _mrna_reasons(row, schema.mrna_features)
        for row_reasons, (_, row) in zip(survival.reasons, prepared.iterrows(), strict=True)
    )
    return EligibilityResult(mask=tuple(not row_reasons for row_reasons in reasons), reasons=reasons)


def normalize_subtype_target(prepared: pd.DataFrame, schema: PreprocessingSchema) -> pd.Series:
    """Map source subtype labels to canonical classes without touching predictors."""
    _required_columns(prepared, (schema.subtype_target_column,), "prepared subtype data")
    mapping = schema.subtype_map

    def normalize(value: object) -> object:
        if _is_missing(value) or value == "NC":
            return pd.NA
        if value in mapping:
            return mapping[str(value)]
        if value in schema.subtype_classes:
            return value
        return pd.NA

    normalized = prepared[schema.subtype_target_column].map(normalize)
    normalized.name = schema.subtype_target_column
    return normalized


def evaluate_subtype_eligibility(
    prepared: pd.DataFrame,
    manifest: pd.DataFrame,
    schema: PreprocessingSchema,
) -> EligibilityResult:
    """Return Track C eligibility independently of survival outcomes."""
    _required_columns(prepared, (schema.subtype_target_column,) + schema.mrna_features, "prepared subtype data")
    splits = _aligned_splits(prepared, manifest)
    mapping = schema.subtype_map
    reasons: list[tuple[EligibilityReasonCode, ...]] = []
    for (_, row), split in zip(prepared.iterrows(), splits, strict=True):
        row_reasons: list[EligibilityReasonCode] = []
        value = row[schema.subtype_target_column]
        if _is_missing(value):
            row_reasons.append(EligibilityReasonCode.MISSING_SUBTYPE)
        elif value == "NC":
            row_reasons.append(EligibilityReasonCode.NC_SUBTYPE)
        elif value not in mapping and value not in schema.subtype_classes:
            row_reasons.append(EligibilityReasonCode.UNSUPPORTED_SUBTYPE)
        row_reasons.extend(_mrna_reasons(row, schema.mrna_features))
        if split not in _ALLOWED_SPLITS:
            row_reasons.append(EligibilityReasonCode.INVALID_LOCKED_SPLIT)
        reasons.append(tuple(row_reasons))
    reason_tuple = tuple(reasons)
    return EligibilityResult(mask=tuple(not row_reasons for row_reasons in reason_tuple), reasons=reason_tuple)
