# R1 Biomedical Domain Reset Design

## Goal

Replace the active auto-insurance prototype with a runnable Streamlit shell for
Breast Cancer Prognosis & Subtype Classification while preserving reusable
engineering infrastructure and the complete legacy history.

## Boundary

R1 is a domain reset only. It contains no CSV/TSV parsing, dataset schema
inference, survival modelling, subtype modelling, gene analysis, model
artifacts, scientific metrics, or patient-specific output. Every analysis page
shows an honest pending-data or pending-model state.

## Legacy preservation

The completed P8 tree is checkpointed before migration. Superseded P1-P8
specifications, plans, and domain documents move under
`docs/legacy/auto-insurance/`, with an index naming the checkpoint commit and
the reason for archival. Changelog and implementation history remain active and
retain their earlier entries.

## Active architecture

`app.py` remains a thin Streamlit entrypoint. `src/ui/shell.py` applies the
existing responsive theme, renders typed navigation, dispatches focused page
renderers, and displays a persistent research-only disclaimer. Layout helpers
remain responsible for safe HTML escaping and consistent pending-state cards.

The active navigation order is:

1. Overview
2. Data / Cohort
3. Survival Analysis
4. Subtype Classification
5. Gene Insights
6. Model Comparison
7. Methodology / About

## Configuration

R1 retains side-effect-free environment parsing and frozen dataclasses but
reduces active settings to `COGNIVEX_ENVIRONMENT` and `COGNIVEX_DEBUG`.
Image, model-confidence, localization, and insurance-policy settings are
removed. Dataset upload limits and modeling settings are deferred until their
implementing increments.

## Contracts

`src/contracts/analysis.py` provides frozen, framework-independent,
JSON-compatible skeletons for dataset validation, cohort summary, model and
experiment metadata, survival output, subtype output, feature importance, and
aggregate analysis. Results carry explicit availability states and safe
messages but no fabricated values. Subtype labels remain free-form and empty
while pending; no taxonomy is frozen before dataset handoff.

## Removal and replacement

The active image upload/validation/quality modules, damage contracts and
labels, mock image adapters, localization code, insurance decision engine, and
their tests are removed. Pillow is removed after its last active consumer is
gone. The theme, responsive CSS, navigation mechanics, AppTest infrastructure,
configuration parsing pattern, and safe rendering utilities remain.

## Safety

The shell states that it is a research and educational prototype, not a
diagnostic medical device, treatment recommendation system, validated clinical
prognosis system, or substitute for qualified oncology care. No treatment or
patient-care recommendation is displayed.

## Verification

R1 requires focused configuration, contract, UI-foundation, and Streamlit
tests; the complete suite; compile and dependency checks; legacy-domain scans;
and a live Streamlit smoke test across all seven pages.
