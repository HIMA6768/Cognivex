"""R4D-P0 train-only METABRIC mutation profiling tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pandas.testing as pdt

from src.contracts import PreprocessingTask
from src.data.metabric import MetabricPaths
from src.data.mutation_profile import (
    profile_canonical_mutations,
    profile_mutations,
    write_mutation_profile_artifacts,
)
from src.preprocessing.metabric import verify_canonical_preprocessing
from src.contracts import PreprocessingTask


ROOT = Path(__file__).resolve().parents[1]
MUTATION_COLUMNS = ("tp53_mut", "pik3ca_mut")


def _prepared(*, heldout_tp53: str = "EGFR_L858R") -> pd.DataFrame:
    return pd.DataFrame(
        {
            "patient_id": ("train-a", "train-b", "validation-a", "test-a"),
            "tp53_mut": ("0", "R175H", heldout_tp53, "0"),
            "pik3ca_mut": ("H1047R", "0", "E545K", "Q546K"),
        }
    )


def _manifest() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "patient_id": ("train-a", "train-b", "validation-a", "test-a"),
            "split": ("train", "train", "validation", "test"),
        }
    )


def test_profile_uses_only_locked_training_rows_for_prevalence_flags_and_burden() -> None:
    """Including held-out mutation calls would leak validation/test evidence into Track D planning."""
    baseline = profile_mutations(_prepared(heldout_tp53="0"), _manifest(), MUTATION_COLUMNS)
    heldout_changed = profile_mutations(_prepared(heldout_tp53="EGFR_L858R"), _manifest(), MUTATION_COLUMNS)

    pdt.assert_frame_equal(baseline.per_gene, heldout_changed.per_gene)
    assert baseline.burden_summary == heldout_changed.burden_summary
    assert baseline.training_patients == 2
    assert baseline.per_gene.loc[0, "train_mutated_count"] == 1
    assert baseline.per_gene.loc[0, "train_non_mutated_count"] == 1
    assert baseline.per_gene.loc[0, "train_prevalence"] == 0.5
    assert bool(baseline.per_gene.loc[0, "retain_ge_10pct"]) is True
    assert baseline.burden_summary["mean"] == 1.0


def test_profile_reconciles_missing_annotations_using_valid_training_denominator() -> None:
    """Treating missing calls as no-mutation would understate prevalence and break reconciliation."""
    prepared = _prepared()
    prepared.loc[0, "tp53_mut"] = ""
    result = profile_mutations(prepared, _manifest(), MUTATION_COLUMNS)

    tp53 = result.per_gene.iloc[0]
    assert (tp53["train_mutated_count"], tp53["train_non_mutated_count"], tp53["missing_count"]) == (1, 0, 1)
    assert tp53["train_prevalence"] == 1.0
    assert tp53["train_mutated_count"] + tp53["train_non_mutated_count"] + tp53["missing_count"] == 2
    assert result.burden_summary["patient_count"] == 2
    assert result.burden_summary["patients_with_any_mutation"] == 2


def test_profile_uses_declared_order_and_writes_deterministic_aggregate_artifacts(tmp_path: Path) -> None:
    """Arbitrary mutation-column ordering or patient-level output would make the evidence irreproducible."""
    result = profile_mutations(_prepared(), _manifest(), MUTATION_COLUMNS)
    second = profile_mutations(_prepared(), _manifest(), MUTATION_COLUMNS)

    pdt.assert_frame_equal(result.per_gene, second.per_gene)
    artifact_paths = write_mutation_profile_artifacts(result, tmp_path)
    written = pd.read_csv(artifact_paths.per_gene_csv)
    burden = pd.read_csv(artifact_paths.burden_csv)
    summary = json.loads(artifact_paths.summary_json.read_text(encoding="utf-8"))

    assert written["raw_column"].tolist() == list(MUTATION_COLUMNS)
    assert written["gene"].tolist() == ["tp53", "pik3ca"]
    assert written["retain_ge_1pct"].tolist() == [True, True]
    assert burden["metric"].tolist()[:3] == ["patient_count", "min_mutations", "p25_mutations"]
    assert summary["training_patients"] == 2
    assert summary["raw_mutation_features"] == 2
    assert "patient_id" not in artifact_paths.burden_csv.read_text(encoding="utf-8")
    assert "best" not in artifact_paths.markdown.read_text(encoding="utf-8").lower()


def test_canonical_profile_is_read_only_and_preserves_track_b_mutation_exclusion() -> None:
    """Profiling must not alter canonical bytes or add mutation fields to the existing Track B contract."""
    paths = MetabricPaths.from_repository_root(ROOT)
    raw_before = hashlib.sha256(paths.raw_csv.read_bytes()).hexdigest()
    prepared_before = hashlib.sha256(paths.prepared_csv.read_bytes()).hexdigest()

    result = profile_canonical_mutations(paths)
    r4_report = verify_canonical_preprocessing(paths)
    declared_mutation_columns = tuple(
        json.loads((paths.metadata_dir / "feature_groups.json").read_text(encoding="utf-8"))["mutation_features"]
    )

    assert result.training_patients == 1332
    assert len(result.per_gene) == 173
    assert result.mutation_columns == declared_mutation_columns
    assert tuple(result.per_gene["raw_column"]) == declared_mutation_columns
    assert result.per_gene.apply(
        lambda row: row.train_mutated_count + row.train_non_mutated_count + row.missing_count == result.training_patients,
        axis=1,
    ).all()
    track_b = next(
        item
        for item in r4_report.tasks
        if item.task is PreprocessingTask.CLINICAL_MRNA_SURVIVAL
    )
    assert not any(name.endswith("_mut_present") for name in track_b.final_feature_names)
    assert track_b.mutation_metadata is None
    assert hashlib.sha256(paths.raw_csv.read_bytes()).hexdigest() == raw_before
    assert hashlib.sha256(paths.prepared_csv.read_bytes()).hexdigest() == prepared_before
    assert PreprocessingTask.CLINICAL_MRNA_SURVIVAL.value == "clinical_mrna_survival"
