# R1 Biomedical Domain Reset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a runnable, research-only Streamlit biomedical shell while removing active auto-insurance behavior and preserving its history.

**Architecture:** Keep the existing thin Streamlit entrypoint, visual theme, safe layout helpers, typed navigation pattern, environment parsing pattern, and AppTest harness. Replace domain modules with pending-only biomedical pages and framework-independent contracts; archive superseded material under `docs/legacy/auto-insurance/`.

**Tech Stack:** Python 3.11+, Streamlit 1.39+, standard-library frozen dataclasses/enums, pytest, Streamlit AppTest.

**Spec:** `docs/superpowers/specs/2026-09-17-r1-biomedical-domain-reset-design.md`

## Global Constraints

- Use the current parent session only; do not spawn subagents.
- Preserve the P8 checkpoint and Git history.
- Keep the exact approved seven-page biomedical navigation order.
- Display a persistent research/educational disclaimer.
- Do not process datasets or implement modeling, inference, feature importance, or scientific metrics.
- Do not freeze molecular subtype labels before dataset handoff.
- Do not scaffold empty future packages.
- Remove Pillow after all active image consumers are removed.

---

### Task 0: Preserve P8

**Files:** Existing P8 working tree.

**Interfaces:** Produces an immutable Git checkpoint before migration changes.

- [x] **Step 1:** Create branch `codex/r1-biomedical-domain-reset`.
- [x] **Step 2:** Commit the unchanged P8 tree as `3cb90f7 checkpoint: preserve completed P8 insurance prototype`.
- [x] **Step 3:** Confirm the branch is clean before R1 artifacts are added.

### Task 1: Define R1 behavior through failing tests

**Files:**
- Modify: `tests/test_config.py`
- Modify: `tests/test_contracts.py`
- Modify: `tests/test_ui_foundation.py`
- Modify: `tests/test_app_shell.py`
- Remove: `tests/test_upload_flow.py`
- Remove: `tests/test_quality_gate.py`
- Remove: `tests/test_mock_adapters.py`
- Remove: `tests/test_decision_engine.py`

**Interfaces:** Tests require domain-neutral `AppSettings`; biomedical contract skeletons; the seven-page navigation; research branding and disclaimer; and pending-only page content.

- [x] **Step 1:** Replace insurance assertions with tests for the approved biomedical behavior and remove obsolete domain tests.
- [x] **Step 2:** Run `python -m pytest -q -p no:cacheprovider` and verify failure because the active implementation still exposes insurance contracts and pages.

### Task 2: Replace configuration and contracts

**Files:**
- Modify: `src/config/__init__.py`
- Modify: `src/config/settings.py`
- Remove: `src/config/uploads.py`
- Remove: `src/config/thresholds.py`
- Remove: `src/config/labels.py`
- Remove: `src/config/inference.py`
- Remove: `src/config/policy.py`
- Modify: `src/contracts/__init__.py`
- Remove: `src/contracts/assessment.py`
- Create: `src/contracts/analysis.py`
- Modify: `.env.example`

**Interfaces:** `AppSettings.from_env(...) -> AppSettings`; frozen serializable biomedical contracts with `AnalysisStatus`, validation issue severity, pending results, metadata, and `AnalysisResult`.

- [x] **Step 1:** Implement the minimal domain-neutral configuration required by failing tests.
- [x] **Step 2:** Implement the biomedical pending-result contracts without scientific values or fixed subtype labels.
- [x] **Step 3:** Run `python -m pytest tests/test_config.py tests/test_contracts.py -q -p no:cacheprovider` and verify success.

### Task 3: Replace the active Streamlit experience

**Files:**
- Modify: `app.py`
- Modify: `src/ui/shell.py`
- Modify: `src/ui/navigation.py`
- Modify: `src/ui/components/layout.py`
- Modify: `src/ui/pages/__init__.py`
- Create: `src/ui/pages/overview.py`
- Create: `src/ui/pages/data_cohort.py`
- Create: `src/ui/pages/survival_analysis.py`
- Create: `src/ui/pages/subtype_classification.py`
- Create: `src/ui/pages/gene_insights.py`
- Modify: `src/ui/pages/model_comparison.py`
- Create: `src/ui/pages/methodology_about.py`
- Remove: `src/ui/pages/assessment.py`
- Remove: `src/ui/pages/model_insights.py`
- Remove: `src/ui/pages/monitoring.py`
- Remove: `src/ui/pages/system_about.py`
- Remove: `src/ui/upload_flow.py`
- Remove: `src/ui/quality_gate.py`
- Remove: `src/adapters/`
- Remove: `src/decision/`

**Interfaces:** `PAGE_RENDERERS` maps every approved `Page` value to one renderer. Every page displays a safe pending state; `render_app()` always renders the research disclaimer.

- [x] **Step 1:** Implement biomedical navigation, branding, status, pages, and persistent disclaimer.
- [x] **Step 2:** Remove active image, adapter, and insurance-decision modules.
- [x] **Step 3:** Run `python -m pytest tests/test_ui_foundation.py tests/test_app_shell.py -q -p no:cacheprovider` and verify success.

### Task 4: Archive legacy material and rewrite active documentation

**Files:**
- Create: `docs/legacy/auto-insurance/README.md`
- Move: superseded P1-P8 plans/specifications and insurance-domain documents into `docs/legacy/auto-insurance/`
- Modify: `README.md`, `CHANGELOG.md`, `docs/architecture.md`, `docs/api_contracts.md`, `docs/setup.md`, `docs/limitations.md`, `docs/model_integration.md`, `docs/ui_design.md`, `docs/user_flow.md`, `docs/implementation_log.md`
- Create: `docs/data.md`, `docs/model_training.md`, `docs/model_evaluation.md`, `docs/testing.md`
- Move: `env.example` into the legacy archive

**Interfaces:** Active documents describe only R1. Legacy documents are clearly marked superseded and point to checkpoint `3cb90f7`.

- [x] **Step 1:** Archive legacy material without deleting its history.
- [x] **Step 2:** Rewrite active project, architecture, setup, safety, contract, UI, testing, data-handoff, and model-handoff documentation.
- [x] **Step 3:** Append R1 entries to the changelog and implementation log without removing prior history.

### Task 5: Dependencies and complete R1 verification

**Files:**
- Modify: `pyproject.toml`
- Modify: `requirements.txt`

**Interfaces:** Runtime retains Streamlit and removes Pillow; pytest remains the test runner.

- [x] **Step 1:** Remove Pillow and update project metadata for the biomedical application.
- [x] **Step 2:** Run the focused tests and full `python -m pytest -q -p no:cacheprovider`.
- [x] **Step 3:** Run `python -m compileall -q app.py src tests`, `python -m pip check`, and `git diff --check`.
- [x] **Step 4:** Scan active code/docs for insurance, vehicle, image-quality, YOLO/CNN/MobileNet/ViT, routing, fast-track, resubmit, and repair-cost residue; allow matches only inside the explicit legacy archive or migration history.
- [x] **Step 5:** Start Streamlit headlessly, verify all seven pages and browser/runtime errors, then stop the server.
- [x] **Step 6:** Review the final diff against every R1 constraint and commit the completed increment.
