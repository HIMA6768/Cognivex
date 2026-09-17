# User flow

## R1

1. Open the Streamlit application.
2. Review the research-prototype status and healthcare disclaimer.
3. Navigate among Overview, Data / Cohort, Survival Analysis, Subtype Classification, Gene Insights, Model Comparison, and Methodology / About.
4. Review honest pending states explaining which verified data or model handoff is required next.

There is no uploader, cohort selector, schema inference, model execution, metric, gene ranking, or patient result in R1.

## Future flow

After approval, R2 may add research-dataset selection or CSV/TSV ingestion. Later increments may add validation, leak-safe preprocessing, censoring-aware survival analysis, subtype classification based on confirmed labels, and model-associated gene insights. Each capability requires its own increment gate.
