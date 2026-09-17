# P3 Assessment Upload Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a safe, persisted vehicle-image upload and preview workflow to the Streamlit Assessment page.

**Architecture:** A configuration-owned upload size limit feeds pure validation and session-state helpers under `src/ui/`. The Assessment renderer consumes those helpers to display an empty, invalid, or ready upload state and does not invoke model or decision behavior.

**Tech Stack:** Python 3.11+, Streamlit, Pillow, pytest, Streamlit AppTest.

**Spec:** `docs/superpowers/specs/2026-09-17-p3-assessment-upload-design.md`

## Global Constraints

- Use the verified Streamlit shell; do not add another frontend.
- Support one JPG/JPEG, PNG, or WEBP image only.
- Enforce `COGNIVEX_MAX_UPLOAD_MB`, defaulting to 10 MB.
- Preserve selected upload state across ordinary reruns and reset it deliberately.
- Do not add quality-gate thresholds, inference, mock predictions, YOLO, routing, or decisions.
- Never trust or persist the uploaded filename as a server-side path.
- Update tests and documentation before the P3 increment gate.

---

### Task 1: Upload configuration and pure validation/state contracts

**Files:**
- Create: `src/config/uploads.py`
- Modify: `src/config/settings.py`
- Modify: `src/config/__init__.py`
- Modify: `.env.example`
- Create: `src/ui/upload_flow.py`
- Test: `tests/test_config.py`
- Create: `tests/test_upload_flow.py`

**Interfaces:**
- `UploadSettings(max_upload_mb: int = 10)` exposes `max_upload_bytes`.
- `AppSettings.upload` is loaded from `COGNIVEX_MAX_UPLOAD_MB`.
- `validate_image_upload(name, mime_type, data, max_upload_bytes)` returns a validated `UploadedImage` or `UploadValidationError`.
- `store_upload`, `selected_upload`, and `reset_upload` operate on an injected mutable session mapping.

- [ ] Write failing tests for default/override/invalid upload-size settings, valid JPEG/PNG/WEBP payloads, unsupported type, empty, oversized, unreadable payloads, state persistence, changed-image analysis reset, and reset behavior.
- [ ] Run `pytest tests/test_config.py tests/test_upload_flow.py -v`; confirm expected failures for missing upload contracts.
- [ ] Add the minimal upload settings, validation, and state helpers.
- [ ] Run the focused tests and then `pytest -q`.

### Task 2: Assessment upload UI and regression coverage

**Files:**
- Modify: `src/ui/pages/assessment.py`
- Modify: `src/ui/theme.py`
- Modify: `tests/test_app_shell.py`

**Interfaces:**
- `assessment.render()` calls `AppSettings.from_env()`, renders the labelled uploader, and delegates all validation/state behavior to `src.ui.upload_flow`.
- The ready state exposes an `Analyze Damage` button and `Upload another image` reset action without producing a prediction.

- [ ] Rewrite the former P2 orientation-only test to require an uploader, supported-format/size/tips copy, Analyze Damage, reset action, and no prediction/result content.
- [ ] Run `pytest tests/test_app_shell.py -v`; confirm the former P2 assertions fail for the expected missing P3 UI.
- [ ] Implement the three visual states and narrowly scoped upload/preview CSS.
- [ ] Run the focused UI tests and then `pytest -q`.

### Task 3: Documentation and P3 verification

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/architecture.md`
- Modify: `docs/setup.md`
- Modify: `docs/limitations.md`
- Modify: `docs/ui_design.md`
- Modify: `docs/user_flow.md`
- Modify: `docs/implementation_log.md`

- [ ] Document the verified file types, max-size setting, session-only persistence, invalid/ready states, Analyze Damage boundary, and deferred P4/P5/P6+ work.
- [ ] Verify every documented command and path exists; scan for fabricated model output or stale P2-only copy.
- [ ] Run `pytest -q` and `python -m compileall -q app.py src tests`.
- [ ] Start Streamlit and verify desktop plus 767px and 390px layouts, upload controls, navigation, and browser errors.
- [ ] Stop the local server and report the P3 increment gate with one next recommended increment.
