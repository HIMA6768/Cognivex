# R2 METABRIC Data Ingestion Design

## Purpose

R2 turns the approved corrected METABRIC handoff into the first repository-owned data boundary for the Cognivex research prototype. It implements ingestion, structural schema validation, patient/sample matching, aggregate cohort summaries, Streamlit session state, and the Data / Cohort page. It does not implement preprocessing for modeling, survival analysis, subtype classification, predictions, gene ranking, or clinical decisioning.

## Canonical package and repository layout

The only canonical data package is `C:\Users\sajal\Downloads\Breast_Cancer_Data_Handoff_Corrected.zip`. Its contents are extracted once into:

```text
data/metabric/
  raw/METABRIC_RNA_Mutation.csv
  prepared/METABRIC_prepared.csv
  metadata/clinical_schema.json
  metadata/subtype_labels.json
  metadata/feature_groups.json
  metadata/dataset_summary.json
  metadata/dataset_provenance.json
  metadata/manifest.csv
  metadata/patient_mapping.csv
  metadata/SHA256SUMS.txt
  README.md
scripts/prepare_data.py
docs/data_strategy.md
```

`METABRIC_RNA_Mutation.csv` is immutable raw source data. The active application reads only `METABRIC_prepared.csv`. Every source path is resolved from the repository root; no application setting contains a machine-specific path or depends on the ZIP after extraction.

The supplied checksum manifest and `dataset_provenance.json` are copied without modification. The direct user-provided provenance block is recorded separately as the active provenance resolution because it supersedes the handoff metadata's stale pending confirmation without rewriting the historical artifact.

## Validation boundary

`src/data/metabric.py` is independent of Streamlit and modeling frameworks. It owns:

- repository-relative `MetabricPaths` construction;
- metadata and CSV loading with standard-library `csv`, `json`, and `hashlib`;
- integrity checks for every checksum-manifest entry;
- required-artifact checks;
- prepared-header validation against the feature-group, clinical-schema, survival-target, and subtype-target metadata;
- raw/prepared column-count and patient-ID uniqueness checks;
- one-to-one patient/sample mapping checks;
- manifest membership, uniqueness, and `train` / `validation` / `test` split checks;
- aggregate cohort summary construction; and
- stable, user-safe issue codes.

The data layer returns typed contract values rather than Streamlit elements. An integrity or structural failure produces a report with errors and no trusted cohort-ready state. Validated data produces aggregate counts only; patient-level rows are neither returned to the UI nor displayed by it.

## Contracts and state

The R1 contract module is extended only for data availability. `AnalysisStatus` gains `DATA_READY` and `DATA_INVALID`. Typed metadata, artifact validation, split counts, and cohort summaries are added without adding model outputs.

`MetabricIngestionResult` carries a `DatasetValidationReport`, `CohortSummary`, dataset metadata, and an immutable aggregate split summary. Streamlit stores this result under a dedicated session-state key after first load, reuses it on page reruns, and offers a safe refresh that rebuilds state from the repository files. It never stores CSV rows in session state.

## Data / Cohort UI

The page automatically loads the canonical package through the data service. It renders:

- source identity and a research-only scope note;
- trusted/untrusted validation state with safe issue messages;
- cohort, matched-sample, and split-level aggregate totals;
- the supplied clinical baseline field names and units;
- the dataset-provided molecular subtype taxonomy and NC exclusion policy;
- the active provenance resolution and a note that historical handoff provenance is retained unchanged; and
- no individual patient IDs, clinical rows, genomic values, predictions, or medical recommendations.

## Preparation reproducibility

The supplied preparation script is adapted only for the repository layout and invoked through repository-relative paths. It must retain the documented transformations: source `overall_survival` inversion, stage normalization, `Positve` correction, mapping, manifest generation, and metadata production. R2 verifies semantic reproducibility using schema, row order, patient IDs, values, mappings, and documented transformations, rather than cross-version byte-identical CSV serialization.

The preparation script's `pandas` and `scikit-learn` requirements are isolated in an optional data-preparation dependency group. The running Streamlit application and its ingestion service do not depend on those packages.

## Testing and verification

Focused tests cover repository paths, checksum pass/fail, missing artifacts, invalid JSON, header/schema mismatch, duplicate IDs, mapping mismatch, invalid manifest partition, valid aggregate summaries, session reuse/refresh, and UI protection against patient-level output. The integration test reads the one canonical package. Invalid fixtures are created only in test temporary directories and never committed as duplicate METABRIC data.

R2 verification includes focused tests, the complete pytest suite, compile and dependency checks, checksum validation, size reporting before commit, a legacy/modeling-residue scan, and a live Streamlit smoke test of the Data / Cohort page.

## Out of scope

No modeling preprocessing, learned imputation, scaling, feature selection, Cox fitting, subtype classifier, prediction, model metric, gene importance, clinical decision, or patient-specific result is introduced in R2. R3 remains the next gated increment.
