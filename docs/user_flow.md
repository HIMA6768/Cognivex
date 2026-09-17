# User flow

## R3

1. Open the Streamlit application.
2. Review the research-prototype status and healthcare disclaimer.
3. Navigate among Overview, Data / Cohort, Survival Analysis, Subtype Classification, Gene Insights, Model Comparison, and Methodology / About.
4. Open Data / Cohort to load the repository-owned canonical package into session-backed aggregate state.
5. Review validation status, cohort/matching/split totals, clinical schema names, subtype taxonomy, provenance resolution, and aggregate R3 data-quality status.
6. Review aggregate survival/event, clinical missingness, subtype/NC policy, genomic, split, and actionable quality findings.
7. Use Refresh validated data to reload the canonical package and recompute its cached quality report after a controlled repository update.

There is no uploader, raw-data editing, patient-row display, model execution, metric, gene ranking, patient result, imputation, encoding, scaling, filtering, or split regeneration in R3.

## Future flow

After approval, R4 may add a leak-safe preprocessing design using R3's aggregate findings. Later increments may add censoring-aware survival analysis, subtype classification based on the confirmed labels, and model-associated gene insights. Each capability requires its own increment gate.
