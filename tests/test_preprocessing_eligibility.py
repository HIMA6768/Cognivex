"""R4 task-specific eligibility and target-normalization tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.contracts import EligibilityReasonCode
from src.data.metabric import MetabricPaths
from src.preprocessing.eligibility import (
    evaluate_clinical_mrna_survival_eligibility,
    evaluate_clinical_survival_eligibility,
    evaluate_subtype_eligibility,
    normalize_subtype_target,
)
from src.preprocessing.schema import PreprocessingSchema, load_preprocessing_schema


ROOT = Path(__file__).resolve().parents[1]


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
        subtype_mapping=(
            ("LumA", "Luminal A"),
            ("LumB", "Luminal B"),
            ("Her2", "Her2"),
            ("Basal", "Basal"),
            ("Normal", "Normal-like"),
            ("claudin-low", "Claudin-low"),
        ),
    )


def _prepared(**overrides: object) -> pd.DataFrame:
    row: dict[str, object] = {
        "patient_id": "P1",
        "age_at_diagnosis": 50.0,
        "tumor_size": 20.0,
        "tumor_stage": "2",
        "lymph_nodes_examined_positive": 1,
        "er_status_measured_by_ihc": "Positive",
        "pr_status": "Positive",
        "her2_status": "Negative",
        "overall_survival_months": 24.0,
        "overall_survival": 1,
        "pam50_+_claudin-low_subtype": "LumA",
        "gene_a": 0.25,
        "gene_b": -0.5,
        "gene_a_mut": "0",
    }
    row.update(overrides)
    return pd.DataFrame([row])


def _manifest(split: str = "train") -> pd.DataFrame:
    return pd.DataFrame([{"patient_id": "P1", "data_source": "METABRIC", "split": split}])


def test_canonical_schema_loads_declared_feature_order() -> None:
    """Sorting or inferring genes from CSV columns would break the canonical feature contract."""
    loaded = load_preprocessing_schema(MetabricPaths.from_repository_root(ROOT))

    assert len(loaded.clinical_features) == 7
    assert len(loaded.mrna_features) == 489
    assert loaded.mrna_features[:3] == ("brca1", "brca2", "palb2")
    assert loaded.mrna_features[-3:] == ("ugt2b15", "ugt2b17", "ugt2b7")
    assert len(loaded.mutation_features) == 173


def test_zero_duration_affects_only_survival_tasks(schema: PreprocessingSchema) -> None:
    """Sharing one global mask would wrongly remove a valid Track C record."""
    prepared = _prepared(overall_survival_months=0, **{"pam50_+_claudin-low_subtype": "claudin-low"})

    clinical = evaluate_clinical_survival_eligibility(prepared, _manifest())
    clinical_mrna = evaluate_clinical_mrna_survival_eligibility(prepared, _manifest(), schema)
    subtype = evaluate_subtype_eligibility(prepared, _manifest(), schema)

    assert clinical.mask == (False,)
    assert clinical.reasons[0] == (EligibilityReasonCode.NON_POSITIVE_SURVIVAL_DURATION,)
    assert clinical_mrna.reasons == clinical.reasons
    assert subtype.mask == (True,)


def test_nc_affects_only_subtype_eligibility(schema: PreprocessingSchema) -> None:
    """Using subtype to filter survival rows would violate the frozen NC policy."""
    prepared = _prepared(**{"pam50_+_claudin-low_subtype": "NC"})

    assert evaluate_clinical_survival_eligibility(prepared, _manifest()).mask == (True,)
    assert evaluate_clinical_mrna_survival_eligibility(prepared, _manifest(), schema).mask == (True,)
    subtype = evaluate_subtype_eligibility(prepared, _manifest(), schema)
    assert subtype.mask == (False,)
    assert subtype.reasons == ((EligibilityReasonCode.NC_SUBTYPE,),)


def test_supported_predictor_missingness_does_not_exclude_survival_rows(schema: PreprocessingSchema) -> None:
    """Eligibility must not duplicate the approved train-only imputation policy."""
    prepared = _prepared(tumor_size=np.nan, er_status_measured_by_ihc=np.nan)

    assert evaluate_clinical_survival_eligibility(prepared, _manifest()).mask == (True,)
    assert evaluate_clinical_mrna_survival_eligibility(prepared, _manifest(), schema).mask == (True,)


@pytest.mark.parametrize(
    ("overrides", "expected_reason"),
    [
        ({"overall_survival_months": np.nan}, EligibilityReasonCode.MISSING_SURVIVAL_DURATION),
        ({"overall_survival_months": "not-a-number"}, EligibilityReasonCode.NON_NUMERIC_SURVIVAL_DURATION),
        ({"overall_survival_months": np.inf}, EligibilityReasonCode.NON_FINITE_SURVIVAL_DURATION),
        ({"overall_survival": np.nan}, EligibilityReasonCode.MISSING_SURVIVAL_EVENT),
        ({"overall_survival": 2}, EligibilityReasonCode.INVALID_SURVIVAL_EVENT),
    ],
)
def test_invalid_survival_targets_have_stable_reasons(overrides, expected_reason) -> None:
    """Collapsing target failures into one opaque flag would break auditability."""
    result = evaluate_clinical_survival_eligibility(_prepared(**overrides), _manifest())

    assert result.mask == (False,)
    assert expected_reason in result.reasons[0]


def test_invalid_locked_split_is_reported_without_reassigning_row() -> None:
    """An invalid split must never trigger a row-order or random fallback assignment."""
    result = evaluate_clinical_survival_eligibility(_prepared(), _manifest("holdout"))

    assert result.mask == (False,)
    assert result.reasons == ((EligibilityReasonCode.INVALID_LOCKED_SPLIT,),)


@pytest.mark.parametrize(
    ("value", "expected_reason"),
    [
        (np.nan, EligibilityReasonCode.MISSING_MRNA_VALUE),
        ("bad", EligibilityReasonCode.NON_NUMERIC_MRNA_VALUE),
        (np.inf, EligibilityReasonCode.NON_FINITE_MRNA_VALUE),
    ],
)
def test_mrna_integrity_is_required_for_tracks_b_and_c(schema, value, expected_reason) -> None:
    """Malformed genomic values must not silently enter either genomic task."""
    prepared = _prepared(gene_a=value)

    for result in (
        evaluate_clinical_mrna_survival_eligibility(prepared, _manifest(), schema),
        evaluate_subtype_eligibility(prepared, _manifest(), schema),
    ):
        assert result.mask == (False,)
        assert expected_reason in result.reasons[0]


def test_subtype_target_normalization_is_separate_from_predictors(schema: PreprocessingSchema) -> None:
    """Moving subtype mapping into X transformation would leak the target."""
    prepared = pd.concat(
        [
            _prepared(patient_id="P1", **{"pam50_+_claudin-low_subtype": "LumA"}),
            _prepared(patient_id="P2", **{"pam50_+_claudin-low_subtype": "NC"}),
            _prepared(patient_id="P3", **{"pam50_+_claudin-low_subtype": "unexpected"}),
        ],
        ignore_index=True,
    )

    target = normalize_subtype_target(prepared, schema)

    assert target.name == "pam50_+_claudin-low_subtype"
    assert target.iloc[0] == "Luminal A"
    assert pd.isna(target.iloc[1])
    assert pd.isna(target.iloc[2])
