# OncoMap R10-B1 UI/UX Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the approved OncoMap Streamlit redesign while preserving the frozen R9/R10-B0 analysis boundary, the model contracts, and all research-only safeguards.

**Architecture:** Keep `AnalysisService` as the sole patient-analysis boundary. Add a small checksum-verified, aggregate-only model-evaluation projection to R9 for frozen R5/R6/R7 metrics. Build the OncoMap experience from reusable Streamlit components and existing page modules; the UI renders contracts but never loads artifacts, pickles, models, or preprocessors.

**Tech Stack:** Python, Streamlit, pandas, NumPy, existing R9/R10-B0 services and contracts, existing test stack.

**Spec:** `docs/superpowers/specs/2026-09-20-oncomap-r10-b1-ui-redesign.md`

## Global Constraints

- OncoMap is visible UI branding only. Preserve Cognivex internal modules, artifacts, history, package names, and frozen identifiers.
- UI patient requests must use only public R9 service contracts. The UI must not load pickles, model artifacts, or preprocessing code, and must not call model prediction APIs directly.
- Preserve exact R9 Track A/B/C field mappings, valid nullable-field behavior, R7 class order, R8 aggregate-only scope, and R10-B0 survival-estimate behavior.
- Do not fit, refit, tune, retrain, or alter R5/R6/R7/R8 artifacts. Do not persist patient inputs, outputs, probabilities, or history.
- The survival chart contains only actual frozen-model values at 12, 36, and 60 months. No interpolated, fabricated, or hardcoded survival values.
- Use research/association language only. Do not add clinical risk categories, treatment advice, patient-specific genomic attribution, SHAP, R11, or R12 work.
- Add no dependency unless an existing stack capability cannot meet an approved requirement.

## Review Focus

1. A visual refactor bypasses the R9 service and drifts from the frozen field/preprocessing contracts.
2. A model-evaluation view reads artifacts directly in UI code or omits checksum verification.
3. Survival cards or chart degrade when `survival_estimates` is absent despite a READY prognosis outcome.
4. Combined patient analysis changes partial-readiness semantics or misorders Track C probabilities.
5. A polished result view accidentally turns aggregate R8 associations or model outputs into clinical, causal, or patient-specific claims.

---

## Task 1: Establish the OncoMap shell, grouped navigation, and reusable presentation primitives

**Files:**

- Modify: `app.py`
- Modify: `src/ui/navigation.py`
- Modify: `src/ui/shell.py`
- Modify: `src/ui/theme.py`
- Modify: `src/ui/components/layout.py`
- Create: `src/ui/components/oncomap.py`
- Modify: `tests/test_app_shell.py`
- Create: `tests/test_ui_oncomap_foundation.py`

**Interfaces:**

- Add a display-route definition in `src/ui/navigation.py` that maps existing page implementation modules to the approved labels and groups: Overview; Patient Analysis, Model Evaluation, Gene Insights; Dataset, Methodology, About.
- Expose `render_page_intro`, `render_metric_card`, `render_status_badge`, `render_workflow_steps`, and `render_research_disclaimer` from `src/ui/components/oncomap.py`.
- Keep existing `Page` values and page modules stable; use display metadata rather than renaming historical navigation identifiers.

- [ ] Write failing AppTest/unit tests that assert the visible OncoMap brand, approved grouped navigation labels, light workspace class hooks, responsive card primitives, and absence of the former long product title in primary navigation.
- [ ] Run `./.venv/Scripts/python.exe -m pytest tests/test_ui_oncomap_foundation.py tests/test_app_shell.py -q`; confirm the foundation assertions fail before implementation.
- [ ] Implement the display-route metadata, dark-navy sidebar grouping, OncoMap branding, reusable cards/badges/workflow/disclaimer helpers, and responsive CSS tokens using the existing Streamlit/CSS approach.
- [ ] Retain a single app-level research disclaimer and let sensitive result components place their concise context-specific disclaimer near results.
- [ ] Rerun the focused foundation tests and the existing shell tests; confirm all pass.
- [ ] Commit the isolated shell work with `feat(r10): add OncoMap shell and navigation`.

## Task 2: Expose checksum-verified aggregate model metrics through the R9 service boundary

**Files:**

- Create: `src/contracts/model_evaluation.py`
- Create: `src/artifacts/model_evaluation.py`
- Create: `src/services/model_evaluation.py`
- Modify: `src/contracts/__init__.py`
- Modify: `src/services/analysis.py`
- Create: `tests/test_model_evaluation_service.py`
- Modify: `tests/test_inference_privacy.py`

**Interfaces:**

- Define frozen, framework-independent views: `SurvivalMetricView`, `ClassificationMetricView`, `ModelEvaluationView`, and a safe `ModelEvaluationOutcome`.
- Add `AnalysisService.get_model_evaluation() -> ModelEvaluationOutcome` as the public aggregate-only R9 projection.
- `src/artifacts/model_evaluation.py` verifies canonical R5/R6/R7 bundle checksums before reading text metrics, then returns only frozen aggregate numbers. It never deserializes a model or returns patient data.
- Include Track A metrics from their frozen lineage location, Track B metrics, validation/test deltas, Track C classification metrics, and the approved mixed-evidence interpretation.

- [ ] Write failing tests for the exact frozen aggregate metrics, safe unavailable output after a corrupted checksum, absence of patient values in contracts, and the public R9 getter as the only UI-consumable source.
- [ ] Run `./.venv/Scripts/python.exe -m pytest tests/test_model_evaluation_service.py tests/test_inference_privacy.py -q`; confirm the projection tests fail before implementation.
- [ ] Implement the typed read-only projection and wire it into `AnalysisService` without changing `analyze()` or patient-track semantics.
- [ ] Assert that the reader verifies checksums before metric-file parsing and that UI-facing errors contain no artifact paths or raw parser failures.
- [ ] Rerun focused tests plus `tests/test_analysis_service.py`; confirm the existing R9 request behavior remains unchanged.
- [ ] Commit with `feat(r10): expose frozen model evaluation metrics`.

## Task 3: Redesign Overview, Model Evaluation, Gene Insights, and Research pages

**Files:**

- Modify: `src/ui/pages/overview.py`
- Modify: `src/ui/pages/model_comparison.py`
- Modify: `src/ui/pages/gene_insights.py`
- Modify: `src/ui/pages/data_cohort.py`
- Modify: `src/ui/pages/methodology_about.py`
- Create: `src/ui/components/charts.py`
- Create: `tests/test_ui_oncomap_research_pages.py`
- Modify: `tests/test_app_shell.py`

**Interfaces:**

- `render_model_evaluation(service)` consumes only `service.get_model_evaluation()`.
- `render_gene_insights(service)` consumes only the aggregate R8 getter and renders all 68 effects through aggregate cards, a ranked association chart, and an expandable table.
- Add distinct methodology and about render entry points behind the existing module so navigation destinations remain independently addressable.
- Chart helpers receive already-approved aggregate data or service-result values only; they do not access files or calculate new model metrics.

- [ ] Write failing AppTests for the Overview hero, the four actual system facts (1,904, 68, 2, 6), workflow and Analyze a Patient CTA, aggregate model status, and correct route selection.
- [ ] Add failing tests for model evaluation cards using frozen R5/R6/R7 values, the required mixed-evidence interpretation, no declared survival-model winner, and unavailable-metrics rendering.
- [ ] Add failing tests that Gene Insights renders 68/24/44 from R8 output, ranks model associations without causal wording, exposes the full expandable 68-row table, and never presents R8 as patient attribution.
- [ ] Add failing tests that Dataset remains aggregate-only and Methodology/About render the approved concise content without invented cohort statistics.
- [ ] Run `./.venv/Scripts/python.exe -m pytest tests/test_ui_oncomap_research_pages.py tests/test_app_shell.py -q`; confirm failures precede the page redesign.
- [ ] Implement page composition and simple charts with native Streamlit primitives. Keep the metric-card and chart spacing aligned with the visual reference while sourcing every value from contracts or approved static dataset facts.
- [ ] Rerun focused page tests and the existing R8/R9 aggregate getter regression tests.
- [ ] Commit with `feat(r10): redesign OncoMap research pages`.

## Task 4: Replace separate track forms with the unified patient-analysis and results journey

**Files:**

- Modify: `src/ui/pages/survival_analysis.py`
- Modify: `src/ui/components/analysis.py`
- Create: `src/ui/components/patient_analysis.py`
- Create: `src/ui/components/results.py`
- Create: `tests/test_ui_patient_analysis.py`
- Modify: `tests/test_ui_r9_integration.py`

**Interfaces:**

- `build_patient_request(values: Mapping[str, object]) -> AnalysisRequest` creates one request with `(TRACK_A, TRACK_B, TRACK_C)` and exact global R9 fields.
- `synthetic_demo_profile() -> dict[str, object]` returns a clearly labelled non-patient profile using only valid values for the frozen seven clinical, fifty expression, and eighteen mutation fields; it performs no write.
- `render_patient_steps`, `render_patient_results`, and `render_survival_estimate_unavailable` own presentation only and receive `AnalysisResponse`/contracts from R9.
- Structured genomic controls are generated strictly from existing frozen feature tuples: fifty expression fields and eighteen mutation fields. No discovery by column type, prefix, or artifact inspection.

- [ ] Write failing request-mapping tests proving a combined submission contains the exact R9 global contract and all three requested tracks, while partial submissions preserve R9 readiness outcomes rather than pre-validating them away.
- [ ] Add failing AppTests for the five visible stages (Clinical, Genomic, Review, Run, Results), structured 50/18 genomic grouping, review/edit behavior, and the explicitly labelled synthetic demo profile.
- [ ] Add failing rendering tests proving Track B is primary when READY, Track A comparison appears only when available, a Track A fallback is safe when Track B is unavailable, and no patient-specific claim says one model is clinically better.
- [ ] Add failing tests for 1/3/5-year cards and a three-point chart using only 12/36/60 month estimates, a safe `survival_estimates is None` state with the log score in Technical details, and exact frozen subtype-bar ordering: Basal, Her2, LumA, LumB, Normal, claudin-low.
- [ ] Add failing tests for safe R9 outcome/global-error rendering, no raw request values in errors, no persistence calls, and R8 presented only as a link to global Gene Insights.
- [ ] Run `./.venv/Scripts/python.exe -m pytest tests/test_ui_patient_analysis.py tests/test_ui_r9_integration.py -q`; confirm red tests before replacing the separate forms.
- [ ] Implement the staged unified form in Streamlit session state, use only `AnalysisService.analyze`, and render results result-first with the exact R10-B0 research disclaimer. Put log partial hazard in a collapsed Technical details section.
- [ ] Rerun focused UI tests and existing R9/R10-B0 contract tests, including survival-estimate interpolation and backward-compatibility tests.
- [ ] Commit with `feat(r10): add unified OncoMap patient analysis`.

## Task 5: Verify responsive delivery, frozen artifacts, documentation, and release readiness

**Files:**

- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/architecture.md`
- Modify: `docs/testing.md`
- Modify: `tests/test_app_shell.py`
- Modify: `tests/test_ui_r9_integration.py`
- Create or modify only a focused UI verification test module when required by the final regression coverage.

**Interfaces:**

- Preserve repository-relative `get_analysis_service()` loading and cache construction.
- Use an AST/import regression guard proving UI modules do not import artifact/model/preprocessing/training internals or call direct prediction APIs.
- Add a documented headless Streamlit health command and desktop/narrow viewport acceptance commands using the project’s existing browser/AppTest tooling.

- [ ] Write failing guard tests for forbidden UI imports and direct artifact/model access, then run their focused command and record the expected failure.
- [ ] Implement only the minimal docs and guard code required for the approved architecture; do not alter model or artifact files.
- [ ] Run focused UI/AppTests: `./.venv/Scripts/python.exe -m pytest tests/test_ui_oncomap_foundation.py tests/test_ui_oncomap_research_pages.py tests/test_ui_patient_analysis.py tests/test_ui_r9_integration.py tests/test_app_shell.py -q`.
- [ ] Run the complete suite: `./.venv/Scripts/python.exe -m pytest -q`.
- [ ] Run `./.venv/Scripts/python.exe -m compileall app.py src tests`, `./.venv/Scripts/python.exe -m pip check`, and `git diff --check`.
- [ ] Run the canonical R5/R6/R7/R8 checksum-verification commands through their existing read-only verifiers and confirm their bytes/hashes are unchanged.
- [ ] Start Streamlit headlessly using the documented command; verify a healthy response plus Overview, Patient Analysis, Model Evaluation, Gene Insights, Dataset, Methodology, and About in desktop and narrow viewports. Check the browser console for rendering errors.
- [ ] Inspect `git status --short`, confirm tracked changes are limited to R10-B1 UI, contract projection, tests, and documentation, and confirm `ai_handoff_data/` remains untracked and untouched.
- [ ] Commit the final documentation and verification evidence with `docs(r10): record OncoMap redesign verification`.

## Plan Self-Review

- [x] All approved spec sections map to one of the five tasks: shared shell, Overview, unified patient flow, results, Model Evaluation, Gene Insights, Dataset, Methodology, About, and final verification.
- [x] The plan preserves OncoMap as UI-only branding and keeps existing Cognivex modules and frozen artifacts intact.
- [x] Patient requests use only `AnalysisService`; the aggregate metric projection is checksum-verified and read-only through R9.
- [x] Survival presentation consumes only the frozen R10-B0 12/36/60-month values and specifies the required unavailable-state fallback.
- [x] The Track C display uses the frozen six-class ordering, and R8 remains global aggregate analysis rather than patient attribution.
- [x] Model comparison preserves the approved mixed-evidence interpretation and never names a clinical winner.
- [x] The tasks require focused tests, full regression, headless Streamlit boot, responsive checks, artifact integrity checks, and a clean tracked worktree.
- [x] No model fitting, retraining, R11/R12 work, direct UI artifact loading, patient persistence, invented clinical output, or unnecessary dependency is included.
