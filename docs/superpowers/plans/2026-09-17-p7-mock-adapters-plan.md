# P7 Deterministic Mock Classification and Localization Adapters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic mock P7 adapters that return P6 contracts without a model runtime.

**Architecture:** Framework-free protocols consume a structural image input. SHA-256 digest mapping and explicit development scenarios create repeatable mock classifications and valid image-relative localization results.

**Tech Stack:** Python 3.11 standard library, existing P4/P5/P6 modules, pytest/AppTest.

**Spec:** `docs/superpowers/specs/2026-09-17-p7-mock-adapters-design.md`

## Global Constraints

- Execute in the parent session only; the user explicitly prohibited subagents.
- All mock output must serialize `mock: true` and must not be presented as real confidence or performance.
- No ONNX Runtime, PyTorch, YOLO, NMS, production preprocessing, label indexes, routing policy, or Streamlit result UI.
- Preserve all P6 frozen severity/damage labels and routing contract-only statuses.

---

### Task 1: Contract extensions and adapter interfaces

**Files:**
- Modify: `src/contracts/assessment.py`, `src/contracts/__init__.py`, `src/config/settings.py`, `src/config/__init__.py`, `.env.example`
- Create: `src/config/inference.py`, `src/adapters/__init__.py`, `src/adapters/interfaces.py`, `src/adapters/mock.py`
- Test: `tests/test_mock_adapters.py`, `tests/test_contracts.py`, `tests/test_config.py`

**Interfaces:**
- Produces: `ClassifierAdapter`, `LocalizationAdapter`, `MockClassifierAdapter`, and `MockLocalizationAdapter`.
- Consumes: any structural image with a digest and dimensions.

- [ ] Write failing deterministic interface, scenario, geometry, metadata, availability, and configuration tests.
- [ ] Run `pytest tests/test_mock_adapters.py tests/test_contracts.py -q` and confirm the missing adapter failure.
- [ ] Implement the minimal contracts, settings, protocols, and mock adapters.
- [ ] Re-run focused P7/P6/P4/P5 tests.

### Task 2: Documentation and verification

**Files:**
- Create: `docs/model_integration.md`
- Modify: `README.md`, `CHANGELOG.md`, `docs/architecture.md`, `docs/api_contracts.md`, `docs/limitations.md`, `docs/implementation_log.md`

- [ ] Document determinism, mock display rules, future replacement interfaces, configuration, and AI-handoff boundaries.
- [ ] Run focused tests, full `pytest -q`, compile/dependency checks, and a Streamlit smoke test.
