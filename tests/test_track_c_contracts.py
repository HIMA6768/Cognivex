from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.contracts import TrackCFeatureContract
from src.data import (
    TRACK_C_CLASS_ORDER,
    TRACK_C_EXCLUDED_LABELS,
    TRACK_C_TARGET_COLUMN,
    load_ordered_track_c_cohorts,
    load_track_c_feature_contract,
    ordered_patient_fingerprint,
)


ROOT = Path(__file__).resolve().parents[1]


def test_track_c_feature_contract_is_exact_ordered_and_genomic_only() -> None:
    contract = load_track_c_feature_contract(ROOT)

    assert len(contract.expression_features) == 50
    assert len(contract.mutation_features) == 18
    assert len(contract.raw_features) == 68
    assert contract.raw_features[:3] == ("gata3", "aurka", "csf1r")
    assert contract.raw_features[-3:] == ("lama2_mut", "ttyh1_mut", "nr3c1_mut")
    assert not set(
        (
            "age_at_diagnosis",
            "tumor_size",
            "tumor_stage",
            "lymph_nodes_examined_positive",
            "er_status_measured_by_ihc",
            "pr_status",
            "her2_status",
        )
    ).intersection(contract.raw_features)


def test_track_c_contract_rejects_wrong_counts_duplicates_and_wrong_suffixes() -> None:
    with pytest.raises(ValueError, match="exactly 50"):
        TrackCFeatureContract(("gene",), tuple(f"gene_{index}_mut" for index in range(18)))
    with pytest.raises(ValueError, match="unique"):
        TrackCFeatureContract(tuple("x" for _ in range(50)), tuple(f"gene_{index}_mut" for index in range(18)))
    with pytest.raises(ValueError, match="mutation suffix"):
        TrackCFeatureContract(tuple(f"gene_{index}" for index in range(49)) + ("bad_mut",), tuple(f"m_{index}_mut" for index in range(18)))


def test_track_c_target_classes_and_exclusions_are_frozen() -> None:
    assert TRACK_C_TARGET_COLUMN == "pam50_+_claudin-low_subtype"
    assert TRACK_C_CLASS_ORDER == ("Basal", "Her2", "LumA", "LumB", "Normal", "claudin-low")
    assert TRACK_C_EXCLUDED_LABELS == ("NC",)


def _synthetic_cohort(contract: TrackCFeatureContract) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    labels = ("Basal", "NC", None, "unsupported", "LumA", "Her2")
    for patient_id, label in zip(("p3", "p1", "p5", "p2", "p6", "p4"), labels, strict=True):
        row = {name: float(index + 1) for index, name in enumerate(contract.expression_features)}
        row.update({name: "0" for name in contract.mutation_features})
        row.update({"patient_id": patient_id, TRACK_C_TARGET_COLUMN: label})
        rows.append(row)
    prepared = pd.DataFrame(rows)
    manifest = pd.DataFrame(
        {
            "patient_id": ("p1", "p2", "p3", "p4", "p5", "p6"),
            "split": ("train", "train", "train", "validation", "validation", "test"),
        }
    )
    return prepared, manifest


def test_track_c_eligibility_excludes_nc_missing_and_unsupported_without_mutation() -> None:
    contract = load_track_c_feature_contract(ROOT)
    prepared, manifest = _synthetic_cohort(contract)
    original = prepared.copy(deep=True)

    cohorts = load_ordered_track_c_cohorts(prepared, manifest, contract=contract)

    assert cohorts.train.patient_ids == ("p3",)
    assert cohorts.validation.patient_ids == ("p4",)
    assert cohorts.test.patient_ids == ("p6",)
    assert cohorts.train.exclusions.nc == 1
    assert cohorts.train.exclusions.missing == 0
    assert cohorts.train.exclusions.unsupported == 1
    assert cohorts.validation.exclusions.missing == 1
    assert prepared.equals(original)


def test_track_c_manifest_order_and_fingerprints_ignore_incidental_dataframe_order() -> None:
    contract = load_track_c_feature_contract(ROOT)
    prepared, manifest = _synthetic_cohort(contract)

    original = load_ordered_track_c_cohorts(prepared, manifest, contract=contract)
    shuffled = load_ordered_track_c_cohorts(
        prepared.sample(frac=1, random_state=17).reset_index(drop=True),
        manifest,
        contract=contract,
    )

    for left, right in zip(original.splits, shuffled.splits, strict=True):
        assert left.patient_ids == right.patient_ids
        assert left.fingerprint == right.fingerprint
        assert left.predictors.equals(right.predictors)
        assert left.targets.equals(right.targets)
        assert left.fingerprint == ordered_patient_fingerprint(left.patient_ids)


def test_canonical_track_c_eligible_counts_and_nc_exclusions() -> None:
    contract = load_track_c_feature_contract(ROOT)
    prepared = pd.read_csv(ROOT / "data/metabric/prepared/METABRIC_prepared.csv", low_memory=False)
    manifest = pd.read_csv(ROOT / "data/metabric/metadata/manifest.csv")

    cohorts = load_ordered_track_c_cohorts(prepared, manifest, contract=contract)

    assert tuple(split.row_count for split in cohorts.splits) == (1330, 285, 283)
    assert tuple(split.exclusions.nc for split in cohorts.splits) == (2, 1, 3)
    assert tuple(split.exclusions.missing for split in cohorts.splits) == (0, 0, 0)
    assert tuple(split.exclusions.unsupported for split in cohorts.splits) == (0, 0, 0)
    assert tuple(split.exclusions.source_rows for split in cohorts.splits) == (1332, 286, 286)
    assert all(tuple(split.targets.unique()) for split in cohorts.splits)
    assert set().union(*(set(split.targets) for split in cohorts.splits)) == set(TRACK_C_CLASS_ORDER)
