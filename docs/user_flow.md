# User flow

## R2

1. Open the Streamlit application.
2. Review the research-prototype status and healthcare disclaimer.
3. Navigate among Overview, Data / Cohort, Survival Analysis, Subtype Classification, Gene Insights, Model Comparison, and Methodology / About.
4. Open Data / Cohort to load the repository-owned canonical package into session-backed aggregate state.
5. Review validation status, cohort/matching/split totals, clinical schema names, subtype taxonomy, and provenance resolution.
6. Use Refresh validated data to reload the canonical package after a controlled repository update.

There is no uploader, raw-data editing, patient-row display, model execution, metric, gene ranking, or patient result in R2.

## Future flow

After approval, R3 may assess data quality and cohort readiness. Later increments may add leak-safe preprocessing, censoring-aware survival analysis, subtype classification based on the confirmed labels, and model-associated gene insights. Each capability requires its own increment gate.
