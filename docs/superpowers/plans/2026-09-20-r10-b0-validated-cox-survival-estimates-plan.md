# R10-B0 Validated Cox Survival Estimates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing R9 prognosis result with validated 12-, 36-, and 60-month survival estimates derived from the frozen R5/R6 Cox fitters, without altering the existing log-partial-hazard output.

**Architecture:** Track A and Track B continue to perform their existing transform-only inference. A shared inference helper invokes each fitted Lifelines `CoxPHFitter.predict_survival_function` with the already-transformed one-row feature frame, validates the three returned values, and places them in a backward-compatible typed prognosis contract. No Streamlit code, artifact, model, or training code performs Cox calculations.

**Tech Stack:** Python, NumPy, pandas, Lifelines, existing Cognivex contracts/inference/services/tests.

## Global Constraints

- Use only the frozen R5/R6 trusted artifacts; never fit, refit, tune, or alter them.
- Use Lifelines public survival prediction at exactly 12, 36, and 60 months; never hardcode percentages.
- Preserve the finite `log_partial_hazard` value and existing request/readiness behavior.
- Reject horizons outside the fitted baseline range; no extrapolation.
- Validate finite probabilities in `[0, 1]` and non-increasing values by horizon.
- Do not persist/log patient input, scores, survival estimates, or curves.
- Do not change Streamlit visual design or start R10-B1.

## Review Focus

- Off-index 12/36/60-month requests must use Lifelines cumulative-hazard interpolation, not direct baseline-survival row lookup.
- A malformed/non-monotonic/non-finite survival result must fail safely before it enters `PrognosisResult`.
- Existing log-partial-hazard callers must retain the same scalar value for an identical transformed row.
- A model whose baseline timeline does not reach 60 months must be rejected rather than extrapolated.
- Typed serialization must expose estimates but never echo request fields.

### Task 1: Typed survival-estimate contract and shared validation

**Files:**
- Modify: `src/contracts/inference.py`
- Modify: `src/inference/_common.py`
- Test: `tests/test_inference_contracts.py`

**Interfaces:**
- Produces `SurvivalProbabilityEstimates` with `survival_probability_1y`, `survival_probability_3y`, `survival_probability_5y` and the required interpretation.
- Extends `PrognosisResult` with `survival_estimates: SurvivalProbabilityEstimates | None`, keeping all existing fields unchanged.
- Produces `cox_survival_estimates(fitter, transformed_values, feature_names, track_name)` for Track A/B.

- [ ] Write failing contract tests for finite/bounded/monotonic estimates and serialization.
- [ ] Run `pytest tests/test_inference_contracts.py -q`; expect absence of the new type/field.
- [ ] Implement the frozen estimate dataclass and contract validation.
- [ ] Run the contract tests; expect pass.
- [ ] Write failing helper tests for public Lifelines agreement, off-index horizons, and baseline-range rejection using synthetic data.
- [ ] Run those tests; expect missing helper failure.
- [ ] Implement the minimal helper using `predict_survival_function(times=[12.0, 36.0, 60.0])`, validating fitted baseline range and output values.
- [ ] Run focused helper tests; expect pass.

### Task 2: Transform-only Track A/B integration and regressions

**Files:**
- Modify: `src/inference/track_a.py`
- Modify: `src/inference/track_b.py`
- Modify: `tests/test_inference_track_a.py`
- Modify: `tests/test_inference_track_b.py`
- Modify: `tests/test_inference_privacy.py`

**Interfaces:**
- Consumes Task 1 helper and exact matrix/frame already constructed by Track A/B.
- Produces a `PrognosisResult` containing unchanged `value` plus validated estimates for each ready Track A/B response.

- [ ] Write failing synthetic Track A and Track B tests asserting 12/36/60 estimates match direct public Lifelines calls and score equality to pre-extension risk calculation.
- [ ] Run the focused track tests; expect missing estimate failure.
- [ ] Pass the already transformed row and exact fitted feature order to the shared helper; do not perform a second transform.
- [ ] Run focused Track A/B/privacy tests; expect pass.
- [ ] Verify no source/artifact writes occur during inference with the existing privacy test.

### Task 3: Verification, documentation, and checkpoint

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/architecture.md`
- Test: focused R10-B0 tests above

- [ ] Document that estimates are frozen-model research estimates, not calibrated clinical prognoses or treatment recommendations.
- [ ] Run focused R10-B0 tests.
- [ ] Run the complete `pytest` suite, `python -m compileall -q app.py src tests`, `python -m pip check`, and `git diff --check`.
- [ ] Verify R5/R6 checksum manifests and their covered artifact hashes are unchanged.
- [ ] Commit only the R10-B0 contract/inference/tests/docs changes.
