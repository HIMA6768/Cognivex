# Architecture

## Current R1 state

`app.py` configures Streamlit and delegates to `src/ui/shell.py`. The shell applies the package-owned theme, renders typed navigation, dispatches focused page renderers, and displays the research-only disclaimer after every page. Pages expose pending states only.

`src/config/settings.py` owns side-effect-free application configuration. `src/contracts/analysis.py` owns frozen, JSON-compatible biomedical contract skeletons independently of Streamlit or any model runtime.

## Navigation

The active order is Overview, Data / Cohort, Survival Analysis, Subtype Classification, Gene Insights, Model Comparison, and Methodology / About.

## Planned increments

```text
R2 dataset ingestion
  -> R3 data validation and quality
  -> R4 leak-safe preprocessing
  -> R5 clinical-only survival baseline
  -> R6 clinical-plus-genomic prognosis
  -> R7 molecular subtype classification
  -> R8 gene importance and biological support
  -> R9 analysis orchestration
  -> R10 results and visualization
```

The exact input schema, subtype taxonomy, preprocessing, model artifacts, and evaluation values remain pending verified data/model handoff.

## Reused infrastructure

- Streamlit entrypoint and renderer registry.
- Responsive theme, accessible focus treatment, and safe layout helpers.
- Frozen dataclass and injected-environment configuration patterns.
- Framework-independent serialization pattern.
- pytest and Streamlit AppTest infrastructure.

The superseded implementation is archived under `docs/legacy/auto-insurance/` and preserved in Git checkpoint `3cb90f7`.
