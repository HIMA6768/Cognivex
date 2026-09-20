# OncoMap R10-B1 UI/UX Redesign Design Specification

## Purpose and scope

OncoMap is the visible product name for the Cognivex Streamlit research prototype. It does not rename internal modules, artifacts, packages, branches, frozen identifiers, or historical documentation.

R10-B1 redesigns the presentation layer only: a judge-friendly research dashboard that explains modeled results in plain English before exposing technical detail. It preserves R9 as the only patient-analysis boundary, R10-B0’s fixed-horizon Cox estimates, exact R7 subtype order, aggregate-only R8 semantics, repository-relative paths, and non-persistence of inputs/results. It does not retrain, refit, tune, alter preprocessing, alter canonical artifacts, create treatment advice, risk groups, patient-specific genomic attribution, SHAP, or new dependencies.

## Visual system

- Dark navy sidebar; white or very-light-gray workspace; restrained blue/teal accents.
- Large readable headings, generous whitespace, rounded white cards, subtle borders and low-elevation shadows.
- One card, chart, badge, and status convention across pages; native Streamlit chart primitives and small package-owned CSS only.
- Responsive wide desktop layout that stacks cards and controls on narrow screens.
- No neon, excessive gradients, animations, raw-table-first layouts, or walls of copy.
- Reference dashboard screenshots inform overall polish and hierarchy only; no layout, brand treatment, or asset is copied literally.
- One concise research disclaimer adjacent to prognosis output; implementation details belong in expanders.

The product title is **OncoMap** and the subtitle is **Breast Cancer Prognosis & Molecular Subtype Analysis**.

## Navigation and routes

The sidebar uses grouped headings and display labels. Existing implementation modules remain in place.

```text
ONCOMAP
  Overview
ANALYSIS
  Patient Analysis
  Model Evaluation
  Gene Insights
RESEARCH
  Dataset
  Methodology
  About
```

| Sidebar group | Display label | Internal renderer target |
|---|---|---|
| ONCOMAP | Overview | `pages.overview` |
| ANALYSIS | Patient Analysis | `pages.survival_analysis` (expanded to the unified journey) |
| ANALYSIS | Model Evaluation | `pages.model_comparison` |
| ANALYSIS | Gene Insights | `pages.gene_insights` |
| RESEARCH | Dataset | `pages.data_cohort` |
| RESEARCH | Methodology | `pages.methodology_about` methodology section |
| RESEARCH | About | `pages.methodology_about` about section |

Navigation state must remain rerun-stable and accessible by keyboard. The implementation may add display-route metadata and two display destinations for Methodology/About, but must not rename the existing `methodology_about.py` module.

## Shared data flow and trust boundary

```
Streamlit widgets
  -> exact raw-field mapping
  -> AnalysisRequest / AnalysisService (R9 only)
  -> typed READY or safe readiness/error outcome
  -> presentation-only cards, tables, and charts
```

- Patient Analysis submits one requested-track tuple selected from Track A, Track B, and Track C using `submit_track_request`; the UI never loads a pickle, calls a model, derives features, or runs preprocessing.
- Track A receives exactly seven clinical fields. Track B receives those seven fields plus the frozen 50 expression and 18 mutation fields. Track C receives the frozen 68 genomic fields. Partial input remains valid: R9 controls `READY`, missing-field, invalid-input, artifact-unavailable, and inference-error behavior.
- R10-B0’s `PrognosisResult.survival_estimates` supplies only actual 12-, 36-, and 60-month Cox outputs. The survival chart is a clearly labelled three-point fixed-horizon chart; it must not draw invented intermediate values or call a Cox fitter from UI code.
- R8 remains a separate aggregate getter and never consumes the current patient request.
- Model Evaluation requires a new **read-only R9 aggregate projection** of checksum-verified R5/R6/R7 textual metric artifacts. The page must not read metrics artifacts directly. The projection returns only frozen aggregate metrics and comparison deltas, never patient rows or predictions.
- Dataset retains existing aggregate R2/R3 state helpers and must not render patient-level data.
- No custom session-history, logs, request/result files, browser storage, or export is introduced. Standard current-widget state is transient UI state only.

## Overview

The overview presents a hero headed “OncoMap”, a one-sentence explanation, and a primary **Analyze a Patient** CTA that navigates to Patient Analysis. It includes four factual summary cards: 1,904 METABRIC patients, 68 genomic features, two prognosis models, and six subtype classes.

A compact workflow reads: **Clinical + Genomic Data → Prognosis Analysis → Molecular Subtype → Genomic Insights**. A compact readiness section shows availability for Track A, Track B, Track C, and aggregate R8 using the cached R9 registry; it does not claim model quality or readiness beyond artifact availability.

## Patient Analysis and results

Patient Analysis is one coherent five-step page:

1. **Clinical details:** labelled structured fields for the seven frozen clinical inputs, plain-language helper text, and exact nullable behavior.
2. **Genomic profile:** collapsed/advanced structured sections for the ordered 50 expression fields and 18 mutation annotations. The UI may provide an explicitly labelled synthetic, non-patient demo profile that populates valid contract values only; it may never substitute, infer, or persist a real profile.
3. **Review / Validate:** concise missing-field/readiness summary supplied by R9; no duplicated ML validation.
4. **Run analysis:** one primary action submits the exact available mapping to requested A/B/C tracks.
5. **Results:** render only current response data in the submit rerun, without a history.

When Track B is READY, it is the primary prognosis presentation; Track A appears as an optional clinical-only comparison if READY. If B is not READY and A is READY, A is primary. If neither is READY, show the actionable R9 readiness state. Do not create patient-specific “better model” claims.

### Survival results

Use three dominant cards for **1 YEAR**, **3 YEARS**, and **5 YEARS**, formatted as percentages only at render time from R10-B0 values. Beneath them, show a native line chart using exactly those three actual horizon values. Place this exact concise disclaimer nearby:

> Model-estimated survival probability from the frozen METABRIC Cox model. Research use only; not a clinically validated prognosis or treatment recommendation.

Move `log_partial_hazard` to a collapsed **Technical details** expander. Never expose it as the primary outcome, create risk categories, or infer percentages from it.

### Molecular subtype results

Show a large subtype card with the predicted frozen R7 label and its model probability. Render a horizontal bar chart in the immutable order: Basal, Her2, LumA, LumB, Normal, claudin-low. Format probabilities as percentages only for display; retain original values internally and do not re-rank class order.

### Genomic insights in results

Patient Analysis may link to, but must not embed or reinterpret, R8’s global results. It must never call R8 a patient attribution.

## Model Evaluation

Render only the frozen aggregate metrics from the R9 read-only metric projection:

| Model | Validation C-index | Test C-index |
|---|---:|---:|
| Track A — Clinical Cox | 0.651 | 0.625 |
| Track B — Clinical + Genomic Cox | 0.645 | 0.641 |

Render frozen deltas as approximately -0.006 validation and +0.016 test, with this fixed interpretation:

> The genomic model performed slightly better on the held-out test cohort, while validation performance was slightly lower. Overall evidence is mixed, so the project does not claim a confirmed generalizable improvement from adding genomics.

Do not declare a winner. Present Track C separately as subtype-classification evidence: test Macro-F1 0.734, weighted F1 0.749, accuracy 0.749, and balanced accuracy 0.719. It must be visibly distinct from survival metrics.

## Gene Insights

The top summary shows **68 Analyzed**, **24 Active**, and **44 Near-zero** from R8’s aggregate outcome. The primary visualization is a ranked horizontal bar chart of strongest absolute model associations, colour-coded only by the existing “higher modeled hazard”, “lower modeled hazard”, and “effectively zero” direction semantics. Each item uses a badge, not a checkbox. A collapsed **View all genomic features** section contains the complete 68-row table. The page must not use causal, protective, risk-gene, or patient-specific language.

## Dataset, Methodology, and About

- **Dataset:** METABRIC, 1,904 prepared patients, 693 prepared columns, and locked 1,332/286/286 train/validation/test split. Explain split consistency. Only include new charts if generated from existing aggregate state; no invented demographics.
- **Methodology:** one visual pipeline and four brief cards: Track A clinical prognosis / Cox proportional hazards; Track B clinical + genomic prognosis / penalized Cox; Track C molecular subtype classification / Random Forest; R8 global genomic association analysis. Technical detail is collapsed.
- **About:** concise project purpose, hackathon/research-prototype status, METABRIC basis, output meaning, and limitations.

## Proposed implementation organization

- Modify `app.py`, `src/ui/shell.py`, `src/ui/navigation.py`, `src/ui/theme.py`, and `src/ui/components/layout.py` for OncoMap branding, grouped navigation, responsive shell, and shared cards/badges/status primitives.
- Extend `src/ui/components/analysis.py` only with presentation functions; add focused components such as `src/ui/components/patient_analysis.py`, `results.py`, and `charts.py` if that keeps the existing module small and reusable.
- Expand existing `overview.py`, `survival_analysis.py`, `model_comparison.py`, `gene_insights.py`, `data_cohort.py`, and `methodology_about.py`; do not rename them.
- Add a narrow `src/services`/`src/contracts` aggregate metric projection only as required for Model Evaluation, preserving the R9 service trust boundary and checksum verification before data use.
- Add page/component and AppTest coverage without introducing non-Streamlit dependencies.

## Acceptance and non-goals

Implementation acceptance requires all listed pages to render, R9 A/B/C request mappings to remain exact, R10-B0 estimates to format only at presentation, subtype probabilities/classes to remain unchanged, R8 to return all 68 effects, aggregate metrics to match frozen artifacts, headless Streamlit boot to pass, no patient persistence, repository-relative paths, and frozen R5/R6/R7/R8 artifact checksums unchanged.

R10-B1 excludes retraining, calibration claims, survival-probability invention, dense UI-generated curves, model/artifact changes, treatment recommendations, clinical risk categories, SHAP, patient-specific gene explanations, deployment work, and R11/R12.
