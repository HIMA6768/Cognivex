"""Read-only R4D-P0 mutation evidence profiling for the locked METABRIC train split."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import pandas as pd

from src.contracts import AnalysisStatus
from src.preprocessing.mutations import MutationAnnotationKind, classify_mutation_annotation
from src.preprocessing.schema import load_preprocessing_schema

from .metabric import MetabricPaths, load_metabric


_PROFILE_COLUMNS = (
    "gene",
    "raw_column",
    "train_mutated_count",
    "train_non_mutated_count",
    "train_prevalence",
    "distinct_nonzero_annotations",
    "missing_count",
    "retain_ge_1pct",
    "retain_ge_2pct",
    "retain_ge_5pct",
    "retain_ge_10pct",
)


@dataclass(frozen=True, slots=True)
class MutationProfileResult:
    """Aggregate-only train-split mutation evidence; never a preprocessing contract."""

    mutation_columns: tuple[str, ...]
    training_patients: int
    per_gene: pd.DataFrame
    burden_summary: dict[str, int | float]

    def summary(self) -> dict[str, object]:
        """Return stable, JSON-compatible aggregate profiling facts."""
        flags = {
            "genes_ge_1pct": "retain_ge_1pct",
            "genes_ge_2pct": "retain_ge_2pct",
            "genes_ge_5pct": "retain_ge_5pct",
            "genes_ge_10pct": "retain_ge_10pct",
        }
        return {
            "training_patients": self.training_patients,
            "raw_mutation_features": len(self.mutation_columns),
            "genes_with_any_mutation": int((self.per_gene["train_mutated_count"] > 0).sum()),
            **{name: int(self.per_gene[column].sum()) for name, column in flags.items()},
            "genes_with_zero_mutations": int((self.per_gene["train_mutated_count"] == 0).sum()),
            "genes_with_missing_values": int((self.per_gene["missing_count"] > 0).sum()),
            "total_missing_annotation_cells": int(self.per_gene["missing_count"].sum()),
            "mutation_burden_summary": self.burden_summary,
        }


@dataclass(frozen=True, slots=True)
class MutationProfileArtifactPaths:
    """Committed aggregate evidence artifacts written by the R4D-P0 script."""

    per_gene_csv: Path
    burden_csv: Path
    summary_json: Path
    markdown: Path


def _locked_training_rows(prepared: pd.DataFrame, manifest: pd.DataFrame) -> pd.DataFrame:
    required_prepared = {"patient_id"}
    required_manifest = {"patient_id", "split"}
    if not required_prepared.issubset(prepared.columns) or not required_manifest.issubset(manifest.columns):
        raise ValueError("prepared data and manifest must include patient_id; manifest must include split")
    if prepared["patient_id"].duplicated().any() or manifest["patient_id"].duplicated().any():
        raise ValueError("prepared data and manifest patient IDs must be unique")
    joined = prepared.merge(
        manifest.loc[:, ["patient_id", "split"]],
        on="patient_id",
        how="inner",
        validate="one_to_one",
    )
    if len(joined) != len(prepared) or len(joined) != len(manifest):
        raise ValueError("prepared data and locked manifest must contain the same patient IDs")
    train = joined.loc[joined["split"] == "train"].copy()
    if train.empty:
        raise ValueError("locked manifest does not contain training patients")
    return train


def _gene_name(raw_column: str) -> str:
    if not raw_column.endswith("_mut"):
        raise ValueError(f"mutation column must end with _mut: {raw_column}")
    return raw_column.removesuffix("_mut")


def profile_mutations(
    prepared: pd.DataFrame, manifest: pd.DataFrame, mutation_columns: tuple[str, ...]
) -> MutationProfileResult:
    """Profile declared mutation annotations using only manifest-confirmed training rows."""
    if not mutation_columns or len(mutation_columns) != len(set(mutation_columns)):
        raise ValueError("mutation columns must be a non-empty ordered unique tuple")
    missing_columns = set(mutation_columns) - set(prepared.columns)
    if missing_columns:
        raise ValueError(f"prepared data is missing declared mutation columns: {sorted(missing_columns)}")

    train = _locked_training_rows(prepared, manifest)
    profiles: list[dict[str, object]] = []
    burden = [0] * len(train)
    for raw_column in mutation_columns:
        present_count = 0
        absent_count = 0
        missing_count = 0
        annotations: set[str] = set()
        for index, value in enumerate(train[raw_column]):
            kind, annotation = classify_mutation_annotation(value)
            if kind is MutationAnnotationKind.PRESENT:
                present_count += 1
                burden[index] += 1
                assert annotation is not None
                annotations.add(annotation)
            elif kind is MutationAnnotationKind.ABSENT:
                absent_count += 1
            else:
                missing_count += 1
        valid_count = present_count + absent_count
        if valid_count == 0:
            raise ValueError(f"mutation column has no valid training annotations: {raw_column}")
        prevalence = present_count / valid_count
        profiles.append(
            {
                "gene": _gene_name(raw_column),
                "raw_column": raw_column,
                "train_mutated_count": present_count,
                "train_non_mutated_count": absent_count,
                "train_prevalence": prevalence,
                "distinct_nonzero_annotations": len(annotations),
                "missing_count": missing_count,
                "retain_ge_1pct": prevalence >= 0.01,
                "retain_ge_2pct": prevalence >= 0.02,
                "retain_ge_5pct": prevalence >= 0.05,
                "retain_ge_10pct": prevalence >= 0.10,
            }
        )

    burden_series = pd.Series(burden, dtype="int64")
    burden_summary: dict[str, int | float] = {
        "patient_count": len(train),
        "min": int(burden_series.min()),
        "p25": float(burden_series.quantile(0.25)),
        "median": float(burden_series.median()),
        "mean": float(burden_series.mean()),
        "p75": float(burden_series.quantile(0.75)),
        "max": int(burden_series.max()),
        "patients_with_zero_mutations": int((burden_series == 0).sum()),
        "patients_with_any_mutation": int((burden_series > 0).sum()),
        "std": float(burden_series.std(ddof=0)),
    }
    return MutationProfileResult(
        mutation_columns=mutation_columns,
        training_patients=len(train),
        per_gene=pd.DataFrame(profiles, columns=_PROFILE_COLUMNS),
        burden_summary=burden_summary,
    )


def profile_canonical_mutations(paths: MetabricPaths | None = None) -> MutationProfileResult:
    """Validate canonical R2 artifacts, then profile their immutable locked training partition."""
    resolved = paths or MetabricPaths.from_repository_root()
    ingestion = load_metabric(resolved)
    if ingestion.validation.status is not AnalysisStatus.DATA_READY:
        raise ValueError("R4D-P0 requires R2 DATA_READY canonical artifacts")
    schema = load_preprocessing_schema(resolved)
    prepared = pd.read_csv(resolved.prepared_csv, low_memory=False)
    manifest = pd.read_csv(resolved.metadata_dir / "manifest.csv")
    return profile_mutations(prepared, manifest, schema.mutation_features)


def _burden_rows(summary: dict[str, int | float]) -> list[dict[str, int | float]]:
    return [
        {"metric": "patient_count", "value": summary["patient_count"]},
        {"metric": "min_mutations", "value": summary["min"]},
        {"metric": "p25_mutations", "value": summary["p25"]},
        {"metric": "median_mutations", "value": summary["median"]},
        {"metric": "mean_mutations", "value": summary["mean"]},
        {"metric": "p75_mutations", "value": summary["p75"]},
        {"metric": "max_mutations", "value": summary["max"]},
        {"metric": "patients_with_zero_mutations", "value": summary["patients_with_zero_mutations"]},
        {"metric": "patients_with_any_mutation", "value": summary["patients_with_any_mutation"]},
        {"metric": "std_mutations", "value": summary["std"]},
    ]


def _markdown(result: MutationProfileResult) -> str:
    summary = result.summary()
    burden = result.burden_summary
    top = result.per_gene.sort_values(
        ["train_prevalence", "train_mutated_count", "gene"],
        ascending=[False, False, True],
        kind="stable",
    ).head(15)
    lines = [
        "# Locked-training mutation profile",
        "",
        "Descriptive R4D-P0 evidence only. Candidate frequency flags do not select a final Track D threshold.",
        "",
        f"- Training patients: {result.training_patients:,}",
        f"- Raw mutation features: {len(result.mutation_columns):,}",
        f"- Genes with any mutation: {summary['genes_with_any_mutation']:,}",
        f"- Genes at candidate >=1% prevalence: {summary['genes_ge_1pct']:,}",
        f"- Genes at candidate >=2% prevalence: {summary['genes_ge_2pct']:,}",
        f"- Genes at candidate >=5% prevalence: {summary['genes_ge_5pct']:,}",
        f"- Genes at candidate >=10% prevalence: {summary['genes_ge_10pct']:,}",
        "",
        "## Mutation burden",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    lines.extend(
        f"| {label} | {burden[key]} |"
        for label, key in (
            ("Minimum", "min"),
            ("25th percentile", "p25"),
            ("Median", "median"),
            ("Mean", "mean"),
            ("75th percentile", "p75"),
            ("Maximum", "max"),
            ("Patients with zero mutations", "patients_with_zero_mutations"),
            ("Patients with any mutation", "patients_with_any_mutation"),
        )
    )
    lines.extend(("", "## Top 15 genes by training prevalence", "", "| Gene | Mutated count | Prevalence |", "| --- | ---: | ---: |"))
    lines.extend(
        f"| {row.gene} | {row.train_mutated_count} | {row.train_prevalence:.6f} |"
        for row in top.itertuples(index=False)
    )
    return "\n".join(lines) + "\n"


def write_mutation_profile_artifacts(
    result: MutationProfileResult, output_dir: Path
) -> MutationProfileArtifactPaths:
    """Write deterministic aggregate evidence artifacts without any patient-level output."""
    output_dir.mkdir(parents=True, exist_ok=True)
    per_gene_csv = output_dir / "mutation_profile_train.csv"
    burden_csv = output_dir / "mutation_burden_train.csv"
    summary_json = output_dir / "mutation_profile_summary.json"
    markdown = output_dir / "mutation_profile_train.md"
    result.per_gene.to_csv(per_gene_csv, index=False)
    pd.DataFrame(_burden_rows(result.burden_summary)).to_csv(burden_csv, index=False)
    summary_json.write_text(json.dumps(result.summary(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown.write_text(_markdown(result), encoding="utf-8")
    return MutationProfileArtifactPaths(per_gene_csv, burden_csv, summary_json, markdown)
