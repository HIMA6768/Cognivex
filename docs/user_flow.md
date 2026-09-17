# User flow

## R4

1. Open the Streamlit application.
2. Review the research-prototype status and healthcare disclaimer.
3. Navigate among Overview, Data / Cohort, Survival Analysis, Subtype Classification, Gene Insights, Model Comparison, and Methodology / About.
4. Open Data / Cohort to load the repository-owned canonical package into session-backed aggregate state.
5. Review validation status, cohort/matching/split totals, clinical schema names, subtype taxonomy, provenance resolution, and aggregate R3 data-quality status.
6. Review aggregate survival/event, clinical missingness, subtype/NC policy, genomic, split, and actionable quality findings.
7. Use Refresh validated data to reload the canonical package and recompute its cached quality report after a controlled repository update.
8. R4 preprocessing remains an internal research-engineering boundary; it does not expose transformed rows or add a patient prediction flow.

There is no uploader, raw-data editing, patient-row display, model execution, metric, gene ranking, patient result, or split regeneration. R4 performs preprocessing only inside tested engineering services and does not render matrices or row-level eligibility.

## Future flow

After approval, R5 may consume Track A for a clinical-only censoring-aware baseline. R6 may consume Track B, and R7 may consume Track C. Each modeling capability requires its own increment gate.
