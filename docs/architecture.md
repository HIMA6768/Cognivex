# Architecture

## Current R4D state

`app.py` configures Streamlit and delegates to `src/ui/shell.py`. The shell applies the package-owned theme, renders typed navigation, dispatches focused page renderers, and displays the research-only disclaimer after every page.

`src/data/metabric.py` resolves repository-relative canonical paths, verifies imported checksums, validates the prepared schema, patient/sample mapping, and manifest, then returns aggregate-only frozen contracts from `src/contracts/analysis.py`. `src/data/metabric_quality.py` runs only after that result is `DATA_READY`; it scans canonical prepared data and R2 metadata read-only, then returns aggregate quality contracts. `src/ui/data_cohort_state.py` also caches the aggregate R4 canonical-preprocessing verification report, allowing the Data / Cohort page to present canonical data-quality warnings separately from `PREPROCESSING_READY`. The page never receives patient rows.

`src/preprocessing/` provides immutable metadata loading, patient-aligned task eligibility, explicit predictor selection, four fresh sklearn-compatible factories, and canonical aggregate verification. R4D adds a shared mutation parser, fit-local binary frequency selector, and all-gene burden transformer. Contracts in `src/contracts/preprocessing.py` remain serializable without Streamlit or sklearn values. Final predictors never expose IDs, targets, split fields, raw mutation annotations, or eligibility metadata.

`src/data/mutation_profile.py` remains the R4D-P0 evidence-only boundary. Its full-training 27-gene result verifies, but does not configure, the production selector. Track D fits selection independently on every training/fold-training input and may retain a different set in future CV.

## Navigation

The active order is Overview, Data / Cohort, Survival Analysis, Subtype Classification, Gene Insights, Model Comparison, and Methodology / About.

## Planned increments

```text
R2 validated data ingestion
  -> R3 data quality review and engineering-readiness findings
  -> R4 leak-safe preprocessing (complete)
  -> R4D Track D mutation preprocessing (complete)
  -> R5 clinical-only survival baseline
  -> R6 clinical-plus-genomic prognosis
  -> R7 molecular subtype classification
  -> R8 gene importance and biological support
  -> R9 analysis orchestration
  -> R10 results and visualization
```

R4/R4D confirm preprocessing readiness only. Model artifacts, predictive fitting, evaluation values, predictions, gene ranking, and clinical interpretation remain pending later approved increments.

## Reused infrastructure

- Streamlit entrypoint and renderer registry.
- Responsive theme, accessible focus treatment, and safe layout helpers.
- Frozen dataclass and injected-environment configuration patterns.
- Framework-independent serialization pattern.
- pytest and Streamlit AppTest infrastructure.

The superseded implementation is archived under `docs/legacy/auto-insurance/` and preserved in Git checkpoint `3cb90f7`.
