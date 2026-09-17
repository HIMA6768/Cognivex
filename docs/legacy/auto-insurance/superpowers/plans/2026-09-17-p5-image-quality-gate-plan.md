# P5 Image Quality Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic configuration-backed image quality reports after P4 structural validation.

**Architecture:** A pure `src/ui/quality_gate.py` consumes P4 `ValidatedImage.preview_data`, computes luminance and Laplacian metrics, and returns typed results. The Assessment page renders quality remediation without introducing routing or inference.

**Tech Stack:** Python 3.11, Pillow, Streamlit, pytest/AppTest.

**Spec:** `docs/superpowers/specs/2026-09-17-p5-image-quality-gate-design.md`

## Global Constraints

- Execute inline in the parent session only; the user explicitly prohibited subagents.
- P5 must not repeat P4 file/format/decode/dimension validation.
- Thresholds are environment-configured, provisional engineering defaults, and not empirically validated.
- No AI, model, YOLO, routing, or decision outputs.

---

### Task 1: Typed quality gate and configuration

**Files:**
- Create: `src/ui/quality_gate.py`
- Modify: `src/config/thresholds.py`, `src/config/settings.py`, `.env.example`
- Test: `tests/test_quality_gate.py`, `tests/test_config.py`

**Interfaces:**
- Consumes: `ValidatedImage` from `src.ui.upload_flow`.
- Produces: `evaluate_quality(image: ValidatedImage, thresholds: QualityThresholds) -> QualityReport`.

- [ ] Write deterministic failing tests for sharp, blurred, dark, bright, boundary, multi-failure, schema, and configuration behavior.
- [ ] Run `pytest tests/test_quality_gate.py tests/test_config.py -q` and confirm the missing module/API failure.
- [ ] Implement frozen typed schemas, thumbnail measurements, and environment parsing.
- [ ] Re-run the focused tests and confirm success.

### Task 2: Streamlit quality presentation

**Files:**
- Modify: `src/ui/pages/assessment.py`
- Test: `tests/test_app_shell.py`

**Interfaces:**
- Consumes: a P4 `ValidatedImage` and P5 `QualityReport`.
- Produces: actionable quality errors while retaining preview/reset behavior.

- [ ] Write failing AppTest coverage for quality-failure copy and disabled analysis.
- [ ] Run `pytest tests/test_app_shell.py -q` and confirm the unmet expectation.
- [ ] Evaluate P5 only after P4 success and render the report without routing or predictions.
- [ ] Re-run AppTest coverage and confirm success.

### Task 3: Documentation and final verification

**Files:**
- Create: `docs/quality_gate.md`
- Modify: `README.md`, `CHANGELOG.md`, `docs/architecture.md`, `docs/setup.md`, `docs/ui_design.md`, `docs/user_flow.md`, `docs/limitations.md`, `docs/implementation_log.md`

- [ ] Document methods, thresholds, provisional selection basis, boundaries, and tuning procedure.
- [ ] Run focused P5 tests, full `pytest -q`, `python -m compileall -q app.py src tests`, `pip check`, and a Streamlit smoke test.
