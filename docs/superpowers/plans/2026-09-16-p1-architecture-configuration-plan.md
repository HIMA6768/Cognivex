# P1 Architecture and Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish a safe, tested Python/Streamlit configuration foundation for the pre-model application.

**Architecture:** A frozen settings boundary under `src/config/` will parse environment variables without external side effects. Canonical labels are defined independently from model artifacts, while model paths and model-dependent thresholds remain optional until AI handoff. Documentation records the Streamlit architecture and the conflict with the existing unrelated deployment template.

**Tech Stack:** P1 uses Python 3.11+, pytest, Streamlit, and standard-library dataclasses/enums/environment parsing. Pillow, NumPy, and OpenCV headless are planned downstream image-processing dependencies.

**Spec:** `docs/superpowers/specs/2026-09-16-p1-architecture-configuration-design.md`

## Global Constraints

- “USE STREAMLIT.”
- “DO NOT train any AI model unless explicitly assigned.”
- “Do NOT decide: real confidence threshold, production classifier, real model preprocessing, real label indices until AI engineer handoff arrives.”
- “If a value is unknown, document: `Pending AI model handoff.`”
- “Do not commit secrets or environment files.”
- “Keep one clear responsibility per module.”
- Existing user changes, including `env.example`, must be preserved.

---

### Task 1: Configuration and canonical label contracts

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `src/__init__.py`
- Create: `src/config/__init__.py`
- Create: `src/config/labels.py`
- Create: `src/config/thresholds.py`
- Create: `src/config/settings.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces `SeverityLabel`, `DamageTypeLabel`, `ThresholdSettings`, `AppSettings`, and `ConfigurationError` for later increments.
- `AppSettings.from_env(environ: Mapping[str, str] | None = None) -> AppSettings` must support deterministic test injection.

- [ ] **Step 1: Write failing tests** for canonical label values, default development settings, environment overrides, optional unset model fields, and invalid boolean/numeric input.
- [ ] **Step 2: Run `pytest tests/test_config.py -v` and verify the tests fail because the configuration modules do not exist.
- [ ] **Step 3: Implement the minimal configuration modules and safe templates. Model-dependent thresholds and paths must remain optional; quality defaults must be labeled provisional.
- [ ] **Step 4: Run `pytest tests/test_config.py -v` and then `pytest -q`; record exact results.
- [ ] **Step 5: Self-review for secret leakage, import stability, and Python-version compatibility.
- [ ] **Step 6: Commit if repository permissions allow; otherwise report the managed `.git` limitation.

### Task 2: Project and architecture documentation

**Files:**
- Create: `README.md`
- Create: `CHANGELOG.md`
- Create: `docs/architecture.md`
- Create: `docs/setup.md`
- Create: `docs/limitations.md`
- Create: `docs/implementation_log.md`

**Interfaces:**
- Documents the configuration variables and the `src/config` contracts from Task 1.
- Must identify the current state as pre-model and state `Pending AI model handoff.` where appropriate.

- [ ] **Step 1: Write documentation covering the actual repository state, supported setup commands, architecture flow, limitations, and this increment.
- [ ] **Step 2: Check every documented path and command against the repository.
- [ ] **Step 3: Run `rg -n "Next.js|Vercel|MongoDB|FastAPI|Pending AI model handoff|Streamlit" README.md docs .env.example` and verify conflicts and pending dependencies are explicit.
- [ ] **Step 4: Self-review for fabricated model metrics, production claims, and secret values.
- [ ] **Step 5: Commit if repository permissions allow; otherwise report the managed `.git` limitation.

### Task 3: Parent integration verification

**Files:**
- Verify: all files from Tasks 1–2

- [ ] **Step 1: Inspect the complete working-tree diff and untracked-file list.
- [ ] **Step 2: Run the full available test suite with `pytest -q`.
- [ ] **Step 3: Run import/config smoke checks without starting Streamlit inference.
- [ ] **Step 4: Confirm no real model artifacts, credentials, or UI features were added.
- [ ] **Step 5: Record the P1 gate status and remaining risks.
