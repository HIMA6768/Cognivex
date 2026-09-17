# P6 Shared Schemas and Integration Contracts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Freeze independent serializable contracts for every planned assessment-pipeline stage.

**Architecture:** Central frozen dataclasses live in `src/contracts/assessment.py`. P4 adapts its existing result to canonical validation output, and P5 imports the canonical quality types without changing its deterministic behavior.

**Tech Stack:** Python 3.11 standard library, existing Pillow/Streamlit application, pytest/AppTest.

**Spec:** `docs/superpowers/specs/2026-09-17-p6-shared-schemas-design.md`

## Global Constraints

- Execute in the parent session only; the user explicitly prohibited subagents.
- No Streamlit, ONNX Runtime, PyTorch, real inference, YOLO inference, routing implementation, or production thresholds.
- Preserve severity labels `minor`, `moderate`, `severe` and damage labels `dent`, `scratch`, `broken_glass`, `structural`.
- Model versions, experiment IDs, preprocessing versions, labels indexes, tensors, shapes, normalization values, and calibrated probabilities remain pending AI handoff.

---

### Task 1: Canonical schemas and P4/P5 compatibility

**Files:**
- Create: `src/contracts/__init__.py`, `src/contracts/assessment.py`
- Modify: `src/ui/upload_flow.py`, `src/ui/quality_gate.py`
- Test: `tests/test_contracts.py`, `tests/test_upload_flow.py`, `tests/test_quality_gate.py`

**Interfaces:**
- Produces: `ValidationResult`, `QualityReport`, `ClassificationResult`, `LocalizationResult`, `RoutingDecision`, and `AssessmentResult`.
- Consumes: P4 `ImageValidationResult` through `to_contract()` and P5 `ValidatedImage` behavior unchanged.

- [ ] Write failing tests for valid construction, fixed enums, JSON serialization, invalid box/metadata/labels, and P4/P5 compatibility.
- [ ] Run `pytest tests/test_contracts.py -q` and confirm the missing schema module failure.
- [ ] Implement frozen types, structural validation, JSON-compatible serialization, P4 adaptation, and canonical P5 imports.
- [ ] Re-run contract and P4/P5 tests.

### Task 2: Documentation and verification

**Files:**
- Create: `docs/api_contracts.md`, `docs/quality_threshold_calibration.md`
- Modify: `README.md`, `CHANGELOG.md`, `docs/architecture.md`, `docs/quality_gate.md`, `docs/limitations.md`, `docs/implementation_log.md`

- [ ] Document type relationships, serialization, AI-handoff boundaries, routing status contracts, and calibration protocol.
- [ ] Run focused tests, full `pytest -q`, `python -m compileall -q app.py src tests`, `pip check`, and a Streamlit smoke test.
