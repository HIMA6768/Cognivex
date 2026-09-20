# R10-A Functional Streamlit UI Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect the existing Streamlit shell to the frozen R9 `AnalysisService` without changing model or inference semantics.

**Architecture:** A small UI-only service accessor caches `AnalysisService.from_canonical_artifacts()` by repository root. Page renderers collect only R9-contract fields, submit an `AnalysisRequest`, and render the typed `AnalysisResponse`; they never open model artifacts or implement preprocessing. R8 is read through the separate R9 aggregate getter.

**Tech Stack:** Python, Streamlit, existing R9 contracts/services, pytest and Streamlit `AppTest`.

**Spec:** User-approved R10-A functional integration request, 2026-09-20.

## Global Constraints

- Keep R5–R9 model/service semantics and canonical artifacts frozen.
- Use R9 public service APIs only; never load pickle models or transform/predict directly in UI code.
- Do not persist request fields, results, predictions, probabilities, or patient identifiers.
- Present only R9 log partial hazard scores, exact subtype outputs, and global R8 effects; no risk categories, survival probabilities, treatment advice, or patient-specific R8 attribution.
- Preserve repository-relative Community Cloud operation and add no dependency.
- R10-B visual redesign, R11, and R12 are out of scope.

## Review Focus

- Partial clinical input must render Track A readiness without blocking the shell.
- Invalid or unknown inputs must surface only safe R9 errors, never tracebacks or values.
- R7 class probabilities must remain in the frozen six-class order even if estimator order changes.
- The cached UI accessor must construct the service once per repository root/rerun cache.
- R8 rendering must remain aggregate-only and expose all 68 effects without model loading in UI code.

### Task 1: Add a UI-only cached R9 service boundary

**Files:**
- Create: `src/ui/analysis_service.py`
- Test: `tests/test_ui_analysis_service.py`

**Interfaces:**
- Produces `get_analysis_service(repository_root: Path | None = None) -> AnalysisService` and `repository_root() -> Path`.
- Consumed by survival, subtype, and gene-insights page renderers.

- [ ] Write a failing test that monkeypatches `AnalysisService.from_canonical_artifacts`, calls the cached accessor twice, and asserts one construction with the repository root.
- [ ] Run `pytest tests/test_ui_analysis_service.py -q`; expect an import failure.
- [ ] Add repository-relative root resolution and `@st.cache_resource` construction; do not add logging or persistence.
- [ ] Run `pytest tests/test_ui_analysis_service.py -q`; expect PASS.
- [ ] Commit the service-boundary task.

### Task 2: Replace pending model pages with R9 request/result rendering

**Files:**
- Create: `src/ui/components/analysis.py`
- Modify: `src/ui/pages/survival_analysis.py`, `src/ui/pages/subtype_classification.py`, `src/ui/pages/gene_insights.py`
- Test: `tests/test_ui_analysis_components.py`, `tests/test_app_shell.py`

**Interfaces:**
- Consumes `AnalysisService.analyze(AnalysisRequest)` and `get_prognostic_feature_analysis()`.
- Produces `render_track_outcome(outcome)`, `render_request_errors(errors)`, `render_r8_analysis(outcome)`, and page `render()` functions.

- [ ] Write failing component tests for READY Track A/B score/disclaimer, READY Track C exact six probabilities, missing/error states, and 68-effect aggregate R8 rendering.
- [ ] Run `pytest tests/test_ui_analysis_components.py -q`; expect an import failure.
- [ ] Implement generic safe typed render helpers; use R9 error/result text only and do not echo values.
- [ ] Add basic forms using exact service `required_fields`: clinical controls for Track A, clinical-plus-genomic fields for Track B, genomic fields for Track C. Submit partial mappings unchanged to R9.
- [ ] Run focused component and AppTest pages; expect PASS and no Streamlit exceptions.
- [ ] Commit the functional page-integration task.

### Task 3: Document and verify the R10-A runtime boundary

**Files:**
- Modify: `README.md`, `CHANGELOG.md`, `docs/architecture.md`, `docs/testing.md`
- Test: `tests/test_ui_analysis_service.py`, `tests/test_ui_analysis_components.py`, `tests/test_app_shell.py`

**Interfaces:**
- Consumes all R10-A UI renderers and frozen R9 public services.
- Produces documented repository-relative, cache-backed Streamlit behavior.

- [ ] Write or extend a failing AST/AppTest check proving UI modules do not import artifact loaders, preprocessing, or model adapters.
- [ ] Run that focused check; expect failure before the guard exists.
- [ ] Add concise R10-A documentation and the UI-boundary regression guard.
- [ ] Run focused UI/R9 regression tests, `pytest -q`, `compileall`, `pip check`, `git diff --check`, then a local Streamlit health/smoke test.
- [ ] Commit documentation and verification evidence, then stop before R10-B.

## Self-Review

- R9 is the only model-facing dependency in the planned UI modules; no R5–R8 contract changes are required.
- Track A/B/C use typed readiness and intended in-memory outputs only; R8 uses the separate aggregate getter.
- The plan contains no fitting, inference duplication, persistence, custom visual overhaul, R10-B, R11, or R12 work.
- The five likely failures in Review Focus each map to a task-level test.
- No placeholder implementation steps remain.
