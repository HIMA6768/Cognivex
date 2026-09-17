from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_DATA_ROOT = REPOSITORY_ROOT / "data" / "metabric"

CLINICAL_FEATURES = [
    "age_at_diagnosis",
    "tumor_size",
    "tumor_stage",
    "lymph_nodes_examined_positive",
    "er_status_measured_by_ihc",
    "pr_status",
    "her2_status",
]
SURVIVAL_TARGETS = ["overall_survival_months", "overall_survival"]
SUBTYPE_TARGET = "pam50_+_claudin-low_subtype"
ID_COLUMNS = ["patient_id"]

SUBTYPE_MAPPING = {
    "LumA": "Luminal A",
    "LumB": "Luminal B",
    "Her2": "Her2",
    "Basal": "Basal",
    "Normal": "Normal-like",
    "claudin-low": "Claudin-low",
}


def _normalize_stage(value: object) -> str:
    """Normalize METABRIC tumor stage to a small categorical contract."""
    if pd.isna(value):
        return "Unknown"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "Unknown"
    if number in (1.0, 2.0, 3.0, 4.0):
        return str(int(number))
    # The uploaded cohort contains four stage=0 rows. Treat these as unknown
    # rather than silently promoting them to a clinically meaningful stage.
    return "Unknown"


def _split_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if not df["patient_id"].is_unique:
        raise ValueError("patient_id must be unique before patient-level splitting")

    # random_state=42 locks a reproducible partition. Reproducibility alone does
    # not prevent leakage; leakage control also requires patient-level uniqueness
    # and training-only fitting of all learned preprocessing/feature selection.
    train_idx, temp_idx = train_test_split(df.index, test_size=0.30, random_state=42)
    val_idx, test_idx = train_test_split(temp_idx, test_size=0.50, random_state=42)

    manifest = pd.DataFrame({
        "patient_id": df["patient_id"],
        "data_source": "METABRIC_Kaggle",
        "split": "train",
    })
    manifest.loc[val_idx, "split"] = "validation"
    manifest.loc[test_idx, "split"] = "test"
    return manifest


def _clinical_missingness(raw_df: pd.DataFrame) -> dict[str, dict[str, object]]:
    handling = {
        "age_at_diagnosis": "No raw missing values; no imputation currently required",
        "tumor_size": "Median imputation fitted on the training split only during modeling",
        "tumor_stage": "Map missing/0 to categorical 'Unknown'",
        "lymph_nodes_examined_positive": "No raw missing values; no imputation currently required",
        "er_status_measured_by_ihc": "Categorical missing-value handling defined/fitted in the training-only preprocessing pipeline",
        "pr_status": "No raw missing values; no imputation currently required",
        "her2_status": "No raw missing values; no imputation currently required",
    }
    result: dict[str, dict[str, object]] = {}
    for column in CLINICAL_FEATURES:
        missing = int(raw_df[column].isna().sum())
        result[column] = {
            "raw_missing_count": missing,
            "raw_missing_pct": round(float(raw_df[column].isna().mean() * 100), 4),
            "handling": handling[column],
        }
    return result


def _split_summary(prepared_df: pd.DataFrame, manifest: pd.DataFrame) -> dict[str, dict[str, object]]:
    joined = prepared_df[["patient_id", "overall_survival", SUBTYPE_TARGET]].merge(
        manifest[["patient_id", "split"]], on="patient_id", how="inner", validate="one_to_one"
    )
    result: dict[str, dict[str, object]] = {}
    for split in ("train", "validation", "test"):
        part = joined[joined["split"] == split]
        event_counts = part["overall_survival"].value_counts().to_dict()
        subtype_counts = part[SUBTYPE_TARGET].fillna("MISSING").value_counts().to_dict()
        result[split] = {
            "patients": int(len(part)),
            "deceased_events": int(event_counts.get(1, 0)),
            "living_or_censored": int(event_counts.get(0, 0)),
            "subtype_counts_raw": {str(k): int(v) for k, v in subtype_counts.items()},
            "subtype_classification_eligible": int((part[SUBTYPE_TARGET].notna() & (part[SUBTYPE_TARGET] != "NC")).sum()),
            "subtype_nc_excluded_track_c": int((part[SUBTYPE_TARGET] == "NC").sum()),
        }
    return result


def _feature_groups(columns: list[str]) -> dict[str, object]:
    try:
        first_mut = next(i for i, col in enumerate(columns) if col.endswith("_mut"))
    except StopIteration as exc:
        raise ValueError("No mutation columns ending in '_mut' were found") from exc

    # In this uploaded merged METABRIC file, columns 0..30 are clinical/targets,
    # columns 31..first *_mut-1 are numeric mRNA Z-score features, and *_mut
    # columns are mutation-call fields.
    first_genomic = 31
    mrna_features = columns[first_genomic:first_mut]
    mutation_features = columns[first_mut:]
    reserved = set(ID_COLUMNS + CLINICAL_FEATURES + SURVIVAL_TARGETS + [SUBTYPE_TARGET])
    other_clinical_metadata = [c for c in columns[:first_genomic] if c not in reserved]

    return {
        "id_columns": ID_COLUMNS,
        "clinical_features": CLINICAL_FEATURES,
        "other_clinical_metadata_not_in_baseline": other_clinical_metadata,
        "mrna_features": mrna_features,
        "mutation_features": mutation_features,
        "survival_targets": SURVIVAL_TARGETS,
        "subtype_target": SUBTYPE_TARGET,
        "feature_counts": {
            "clinical_features": len(CLINICAL_FEATURES),
            "other_clinical_metadata_not_in_baseline": len(other_clinical_metadata),
            "mrna_features": len(mrna_features),
            "mutation_features": len(mutation_features),
        },
        "notes": {
            "mrna_boundary": "Columns after the first 31 METABRIC clinical/target columns and before the first *_mut column in the uploaded merged file.",
            "mutation_boundary": "Columns whose names end in *_mut.",
            "training_rule": "Any learned filtering, imputation, scaling, encoding, or feature selection must be fitted on the training split only.",
        },
    }


def prepare_dataset(raw_csv: Path, output_root: Path) -> None:
    """Rebuild prepared METABRIC artifacts without modifying the raw source CSV."""
    raw_csv = Path(raw_csv)
    output_root = Path(output_root)
    prepared_dir = output_root / "prepared"
    metadata_dir = output_root / "metadata"
    prepared_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)
    prepared_csv = prepared_dir / "METABRIC_prepared.csv"

    print(f"Loading data from: {raw_csv}")
    raw_df = pd.read_csv(raw_csv, low_memory=False)
    raw_df.columns = raw_df.columns.str.strip().str.lower().str.replace(" ", "_", regex=False)

    required = set(ID_COLUMNS + CLINICAL_FEATURES + SURVIVAL_TARGETS + [SUBTYPE_TARGET])
    missing_columns = sorted(required - set(raw_df.columns))
    if missing_columns:
        raise ValueError(f"Required columns missing: {missing_columns}")

    raw_event_counts = raw_df["overall_survival"].value_counts(dropna=False).to_dict()

    prepared = raw_df.copy()
    # Correct a source typo documented in the uploaded Kaggle-derived file.
    prepared = prepared.replace("Positve", "Positive")
    # Missing and stage=0 are represented explicitly as Unknown. Valid stages are
    # normalized to categorical strings 1..4.
    prepared["tumor_stage"] = prepared["tumor_stage"].map(_normalize_stage)
    # Uploaded source convention: 1=Living, 0=Deceased. Application convention:
    # 1=Deceased/Event, 0=Living/Censored for survival modeling.
    source_event = pd.to_numeric(prepared["overall_survival"], errors="raise")
    if not set(source_event.unique()).issubset({0, 1}):
        raise ValueError("overall_survival must be binary before event inversion")
    prepared["overall_survival"] = 1 - source_event.astype(int)

    prepared.to_csv(prepared_csv, index=False)
    print(f"Saved canonical prepared dataset: {prepared_csv}")

    mapping = pd.DataFrame({
        "patient_id": prepared["patient_id"],
        "genomic_sample_id": prepared["patient_id"],
        "mapping_rule": "1:1 patient_id mapping in uploaded merged METABRIC file",
    })
    mapping.to_csv(metadata_dir / "patient_mapping.csv", index=False)

    manifest = _split_dataframe(prepared)
    manifest.to_csv(metadata_dir / "manifest.csv", index=False)

    schema = {
        "input_features": {
            "age_at_diagnosis": {"type": "float", "unit": "years", "required": True, "nullable": False},
            "tumor_size": {"type": "float", "unit": "mm", "required": True, "nullable": True, "missing_policy": "training-only median imputation"},
            "tumor_stage": {"type": "categorical", "categories": ["1", "2", "3", "4", "Unknown"], "required": True, "nullable": False, "missing_policy": "missing/0 mapped to Unknown during canonical preparation"},
            "lymph_nodes_examined_positive": {"type": "integer", "unit": "count", "required": True, "nullable": False},
            "er_status_measured_by_ihc": {"type": "categorical", "categories": ["Positive", "Negative"], "required": True, "nullable": True, "missing_policy": "training-only categorical missing handling"},
            "pr_status": {"type": "categorical", "categories": ["Positive", "Negative"], "required": True, "nullable": False},
            "her2_status": {"type": "categorical", "categories": ["Positive", "Negative"], "required": True, "nullable": False},
        },
        "survival_targets": {
            "time_column": "overall_survival_months",
            "time_unit": "months",
            "event_column": "overall_survival",
            "event_coding": {"0": "Living / Censored", "1": "Deceased (Event)"},
            "source_event_coding_before_preparation": {"0": "Deceased", "1": "Living"},
        },
        "schema_status": "EARLY_DATA_HANDOFF",
    }
    (metadata_dir / "clinical_schema.json").write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")

    feature_groups = _feature_groups(prepared.columns.tolist())
    (metadata_dir / "feature_groups.json").write_text(json.dumps(feature_groups, indent=2) + "\n", encoding="utf-8")

    prepared_event_counts = prepared["overall_survival"].value_counts().to_dict()
    summary = {
        "dataset_name": "METABRIC (Molecular Taxonomy of Breast Cancer International Consortium)",
        "cohort_size_patients": int(len(prepared)),
        "matched_genomic_samples": int(mapping["genomic_sample_id"].nunique()),
        "patient_id_unique": bool(prepared["patient_id"].is_unique),
        "survival_event_counts": {
            "deceased_events": int(prepared_event_counts.get(1, 0)),
            "living_or_censored": int(prepared_event_counts.get(0, 0)),
        },
        "raw_source_event_counts_before_inversion": {str(k): int(v) for k, v in raw_event_counts.items()},
        "missingness_summary": {
            "clinical_features": _clinical_missingness(raw_df),
            "genomic_features": {
                "mrna_selected_block_missing_cells": int(prepared[feature_groups["mrna_features"]].isna().sum().sum()),
                "note": "Missingness reported on the uploaded merged file; model-time preprocessing remains training-only.",
            },
        },
        "split_summary": _split_summary(prepared, manifest),
        "subtype_policy": {
            "taxonomy_column": SUBTYPE_TARGET,
            "mapping": SUBTYPE_MAPPING,
            "nc_policy": "NC is retained for survival Tracks A/B when survival data are valid and excluded only from Track C subtype classification.",
        },
    }
    (metadata_dir / "dataset_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    provenance = {
        "dataset_name": "METABRIC (Molecular Taxonomy of Breast Cancer International Consortium)",
        "distribution_channel": "Kaggle",
        "exact_source_url": None,
        "dataset_version": None,
        "license": None,
        "provenance_status": "PENDING_CONFIRMATION",
        "notes": "The supplied handoff identifies METABRIC via Kaggle but does not provide the exact Kaggle URL, dataset version/date, or license. These fields are intentionally left null until confirmed by the data engineer.",
    }
    (metadata_dir / "dataset_provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")

    print("Verified application event coding (1=Deceased/Event, 0=Living/Censored):")
    print(prepared["overall_survival"].value_counts().sort_index())
    print("Generated manifest, patient mapping, clinical schema, feature groups, dataset summary, and provenance metadata.")


def main() -> None:
    prepare_dataset(CANONICAL_DATA_ROOT / "raw" / "METABRIC_RNA_Mutation.csv", CANONICAL_DATA_ROOT)


if __name__ == "__main__":
    main()
