# P8 Policy-Only Routing Decision Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a pure, deterministic P8 routing policy over P5/P6/P7 contract outputs.

**Architecture:** Add frozen policy configuration under `src/config`, and a new `src/decision` package split into stable reasons, narrow conflict detection, and precedence-owned evaluation. Reuse P6 `RoutingDecision` and keep Streamlit and P7 adapters unchanged.

**Tech Stack:** Python 3.11+, frozen dataclasses/enums, pytest.

**Spec:** `docs/superpowers/specs/2026-09-17-p8-policy-routing-design.md`

## Global Constraints

- No real inference, ONNX Runtime, YOLO processing, UI result rendering, persistence, insurance approval/rejection, or repair-cost estimation.
- All score thresholds are configuration-backed **PROVISIONAL DEVELOPMENT POLICY** defaults, not calibrated probabilities.
- Do not spawn subagents unless genuinely blocked.
- Preserve P3–P7 behavior and P6 contracts.

---

### Task 1: Policy configuration

**Files:**
- Create: `src/config/policy.py`
- Modify: `src/config/settings.py`
- Modify: `src/config/__init__.py`
- Modify: `.env.example`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `PolicySettings(min_severity_score, min_damage_type_score, min_localization_conflict_score, conflict_pairs)` and `AppSettings.policy`.

- [ ] Write failing configuration tests for defaults, environment overrides, invalid thresholds, and canonical conflict pairs.
- [ ] Run `python -m pytest tests/test_config.py -q` and confirm the missing policy surface fails.
- [ ] Implement the frozen policy settings and environment parsing with `[0, 1]` validation.
- [ ] Run `python -m pytest tests/test_config.py -q` and confirm it passes.

### Task 2: Pure decision engine

**Files:**
- Create: `src/decision/__init__.py`
- Create: `src/decision/reasons.py`
- Create: `src/decision/conflicts.py`
- Create: `src/decision/engine.py`
- Test: `tests/test_decision_engine.py`

**Interfaces:**
- Consumes: P6 `QualityReport`, `ClassificationResult`, optional `LocalizationResult`, and `PolicySettings`.
- Produces: `evaluate_routing(...) -> RoutingDecision`.

- [ ] Write table-driven failing tests for quality precedence, unavailable classification, moderate/severe severity, low/missing scores, exact boundaries, zero/unavailable localization, configured conflict, multiple reasons, and minor eligibility.
- [ ] Run `python -m pytest tests/test_decision_engine.py -q` and confirm imports/behavior fail because P8 is absent.
- [ ] Implement centralized `DecisionReasonCode` and safe messages.
- [ ] Implement configured conflict detection for only explicit conflict pairs above the localization threshold.
- [ ] Implement precedence-ordered `evaluate_routing` and preserve P5 failure details.
- [ ] Run `python -m pytest tests/test_decision_engine.py -q` and confirm it passes.

### Task 3: P7 compatibility and documentation

**Files:**
- Modify: `tests/test_decision_engine.py`
- Create: `docs/decision_policy.md`
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/api_contracts.md`
- Modify: `docs/limitations.md`
- Modify: `docs/quality_threshold_calibration.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/implementation_log.md`

**Interfaces:**
- Consumes: actual P7 mock adapter outputs.
- Produces: documented mock-only routing compatibility without model-performance claims.

- [ ] Add a failing integration test that routes actual deterministic P7 mock classification/localization outputs.
- [ ] Implement only the compatibility needed by the existing engine interface.
- [ ] Document precedence, reason codes, provisional thresholds, conflict scope, mock limitations, and deferred capabilities.
- [ ] Run focused P8 tests and confirm they pass.

### Task 4: Increment verification

**Files:**
- Verify all modified P8 files and existing Streamlit shell.

**Interfaces:**
- Produces: P8 increment-gate evidence.

- [ ] Run `python -m pytest tests/test_decision_engine.py tests/test_config.py -q`.
- [ ] Run `python -m pytest -q`.
- [ ] Run `python -m compileall -q app.py src tests`.
- [ ] Run `python -m pip check`.
- [ ] Start Streamlit headlessly, verify the Assessment shell renders without browser console errors, and stop it.
