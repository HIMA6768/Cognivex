# Architecture

## Current R3 state

`app.py` configures Streamlit and delegates to `src/ui/shell.py`. The shell applies the package-owned theme, renders typed navigation, dispatches focused page renderers, and displays the research-only disclaimer after every page.

`src/data/metabric.py` resolves repository-relative canonical paths, verifies imported checksums, validates the prepared schema, patient/sample mapping, and manifest, then returns aggregate-only frozen contracts from `src/contracts/analysis.py`. `src/data/metabric_quality.py` runs only after that result is `DATA_READY`; it scans canonical prepared data and R2 metadata read-only, then returns aggregate quality contracts. `src/ui/data_cohort_state.py` caches both aggregate contracts. The Data / Cohort page never receives patient rows.

## Navigation

The active order is Overview, Data / Cohort, Survival Analysis, Subtype Classification, Gene Insights, Model Comparison, and Methodology / About.

## Planned increments

```text
R2 validated data ingestion
  -> R3 data quality review and engineering-readiness findings
  -> R4 leak-safe preprocessing
  -> R5 clinical-only survival baseline
  -> R6 clinical-plus-genomic prognosis
  -> R7 molecular subtype classification
  -> R8 gene importance and biological support
  -> R9 analysis orchestration
  -> R10 results and visualization
```

R3 confirms only the defined engineering-quality checks and records aggregate limitations. Preprocessing, model artifacts, training behavior, evaluation values, predictions, and clinical interpretation remain pending later approved increments.

## Reused infrastructure

- Streamlit entrypoint and renderer registry.
- Responsive theme, accessible focus treatment, and safe layout helpers.
- Frozen dataclass and injected-environment configuration patterns.
- Framework-independent serialization pattern.
- pytest and Streamlit AppTest infrastructure.

The superseded implementation is archived under `docs/legacy/auto-insurance/` and preserved in Git checkpoint `3cb90f7`.
