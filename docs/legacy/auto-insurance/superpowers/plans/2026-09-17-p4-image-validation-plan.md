# P4 Image Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate supported uploaded vehicle images structurally and prepare a safe normalized preview without adding quality or AI logic.

**Architecture:** Frozen configuration adds structural image limits. The existing pure upload-flow module owns typed validation results, decoding, dimension/decompression safeguards, filename sanitization, mode normalization, and session-state compatibility. The Assessment page only renders its outcome.

**Tech Stack:** Python 3.11+, Streamlit, Pillow, pytest, Streamlit AppTest.

**Spec:** `docs/superpowers/specs/2026-09-17-p4-image-validation-design.md`

## Global Constraints

- Support JPG/JPEG/PNG/WEBP still images only.
- Keep filenames display-only; do not write user files or construct storage paths.
- Enforce configured bytes, min/max dimensions, and max pixels before normalization.
- Return uppercase stable validation codes and user-safe messages.
- Normalize opaque/grayscale content to RGB and alpha content to RGBA for the preview.
- Apply EXIF orientation to preview bytes and reject animated files.
- Do not add blur, brightness, darkness, quality scores, resubmission logic, AI, YOLO, routing, or decisions.

---

### Task 1: Configuration and pure validation contracts

**Files:**
- Modify: `src/config/thresholds.py`
- Modify: `src/config/settings.py`
- Modify: `.env.example`
- Modify: `src/ui/upload_flow.py`
- Modify: `tests/test_config.py`
- Modify: `tests/test_upload_flow.py`

**Interfaces:**
- `ThresholdSettings` adds `max_image_width`, `max_image_height`, and `max_image_pixels`.
- `ImageValidationLimits` holds positive runtime limits.
- `ImageValidationResult` exposes `image` or typed `failure`.
- `ImageValidationFailure.code` is an `ImageValidationCode` enum value.

- [ ] Write failing tests for parsed limits, valid JPEG/PNG/WEBP/grayscale/RGBA inputs, safe Unicode basename handling, malformed/truncated content, suffix/content mismatch, minimum/maximum/pixel dimensions, animated WebP, orientation normalization, and session-state compatibility.
- [ ] Run `pytest tests/test_config.py tests/test_upload_flow.py -v`; verify failures identify missing P4 contracts.
- [ ] Implement the smallest configuration and pure validation changes that satisfy those contracts.
- [ ] Run the focused tests and `pytest -q`.

### Task 2: Assessment presentation and regression coverage

**Files:**
- Modify: `src/ui/pages/assessment.py`
- Modify: `tests/test_app_shell.py`

**Interfaces:**
- `assessment.render()` constructs `ImageValidationLimits` from `AppSettings` and passes it to `validate_image_upload()`.
- Invalid P4 results render the typed user-safe message using `st.error` and retain the P3 reset action.

- [ ] Extend AppTest coverage with an undersized supported image that surfaces `IMAGE_TOO_SMALL` guidance rather than a traceback.
- [ ] Run the focused AppTest; confirm the new test fails before the page consumes P4 limits.
- [ ] Wire the page to configured limits and normalized preview bytes.
- [ ] Run focused tests and `pytest -q`.

### Task 3: Documentation and increment gate

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/architecture.md`
- Modify: `docs/setup.md`
- Modify: `docs/limitations.md`
- Modify: `docs/ui_design.md`
- Modify: `docs/user_flow.md`
- Modify: `docs/implementation_log.md`

- [ ] Document the P4 codes, structural limits, normalized preview contract, EXIF/animation policy, and P5-only quality checks.
- [ ] Verify documented paths and commands; scan for fabricated quality or AI claims.
- [ ] Run `pytest -q`, `python -m compileall -q app.py src tests`, `pip check`, and `git diff --check`.
- [ ] Start Streamlit and verify the actionable empty/error UI, navigation, desktop appearance, and browser error log; stop the server before reporting the P4 gate.
