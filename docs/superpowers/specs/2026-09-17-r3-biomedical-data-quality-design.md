# R3 Biomedical Data Quality Validation Design

## Purpose

R3 assesses whether the canonical, structurally validated METABRIC cohort is usable for later engineering work and records its limitations. It does not make a clinical-quality judgment, modify data, or build a model.

## Boundary

R2 remains the sole owner of artifact paths, SHA-256 verification, schema identity, manifest loading, and patient/sample mapping. R3 first calls `load_metabric()` (or receives its cached result) and proceeds only when its validation status is `DATA_READY`. A failed R2 result becomes a blocking `R2_<issue-code>` quality finding; R3 does not attempt to repair or bypass it.

`src/data/metabric_quality.py` reads the repository-owned prepared CSV and the existing R2 metadata, manifest, and mapping files. It may hold identifier sets transiently while checking consistency, but its public result contains aggregates only.

## Contracts

The following framework-independent contracts live with the existing analysis contracts:

- `DataQualitySeverity`: `ERROR`, `WARNING`, `INFORMATION`.
- `DataQualityStatus`: `DATA_QUALITY_READY`, `DATA_QUALITY_READY_WITH_WARNINGS`, `DATA_QUALITY_BLOCKED`.
- `DataQualityFinding`: stable code, severity, user-safe title/message, affected count/fraction, optional field/group, and a recommendation.
- `DataQualityReport`: status, ordered findings, severity counts, and aggregate survival, clinical-missingness, split, subtype, and genomic summaries.

`DataQualityReport` is deterministic and serializable. It intentionally has no generated timestamp: timestamps would make equivalent scans differ without reflecting a data change.

## Rule Set

`QualityRules` centralizes a single engineering observation: durations above 1,200 months are reported as suspicious information. This is a 100-year plausibility sentinel for data review, not a clinical threshold and never rejects records. It is documented and injectable for controlled tests.

Errors block downstream engineering: R2 failure, missing required columns or identifiers, duplicate IDs, invalid/missing survival targets, event values outside canonical `{0, 1}`, malformed manifest/mapping, missing or duplicate expected feature columns, non-numeric/infinite genomic values, and unexpected declared clinical or subtype categories.

Warnings require a later R4 data-handling decision but do not mutate anything: zero survival durations, missing nullable clinical values, missing genomic values, missing subtype labels, and zero-variance genomic features. R3 treats declared mRNA features as numeric measurements; the handoff's `*_mut` fields are mutation annotations (including `0` for no annotation), so it checks them for missingness and constant values without inventing a numeric encoding.

Information reports cohort size, event/censor counts, distributions by locked split, subtype counts and imbalance, the NC policy/count, accepted `Unknown` tumor-stage count, feature counts, and the suspicious-duration observation.

`Unknown` is an allowed canonical tumor-stage category. It is reported prominently but never treated as malformed. `NC` rows remain in the canonical cohort; the report repeats the declared policy that they are eligible for later survival tracks when survival data is valid and excluded only from later subtype-classifier training.

## Scan Flow

```text
R2 MetabricIngestionResult
  ├─ not DATA_READY → DATA_QUALITY_BLOCKED, R2-derived ERROR findings
  └─ DATA_READY
       └─ prepared CSV + schema + feature groups + subtype labels + mapping + manifest
            ├─ identifier/mapping/split checks
            ├─ survival target checks
            ├─ clinical schema and missingness checks
            ├─ genomic integrity and aggregate missingness checks
            └─ subtype mapping, NC policy, and aggregate distributions
                 → DataQualityReport
```

The scan is read-only. It never imputes, encodes, scales, filters, balances, selects genes, regenerates the manifest, drops rows, fits models, or produces predictions.

## Streamlit Integration

The existing Data / Cohort page gains a cached R3 report keyed to the validated R2 result. Refreshing the cohort also refreshes the report. The page renders only aggregate status, counts, distributions, and concise findings; it does not expose a dataframe of patient rows, patient identifiers, genomic values, or long feature-name lists.

## R3/R4 Boundary

R3 supplies R4 with missingness, type, variance, distribution, and structural findings. R4 now provides the applicable training-split-only preprocessing and eligibility policies; R3 continues to report canonical facts without prescribing or performing those transformations.
