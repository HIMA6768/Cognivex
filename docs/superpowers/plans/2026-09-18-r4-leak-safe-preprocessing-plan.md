# R4 Leak-Safe Preprocessing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add train-only, task-specific, sklearn-compatible preprocessing and eligibility contracts for METABRIC Tracks A, B, and C without fitting predictive models.

**Architecture:** R4 gates on R2/R3, aligns canonical rows to the locked manifest by patient ID, computes independent task masks, and builds explicit fresh preprocessors for each task. Shared helpers enforce schema, exact missing-indicator names, deterministic feature order, mRNA integrity, and fail-loud leakage protection while target normalization remains outside predictor transformation.

**Tech Stack:** Python 3.11+, dataclasses, pandas, NumPy, scikit-learn, pytest, Streamlit smoke verification.

**Spec:** `docs/superpowers/specs/2026-09-18-r4-leak-safe-preprocessing-design.md`

## Global Constraints

- Keep subagents off and execute in the current parent session.
- Preserve R2 ingestion and R3 quality behavior and require their readiness before canonical R4 work.
- Never mutate canonical raw, prepared, manifest, mapping, schema, subtype, provenance, or checksum artifacts.
- Preserve the locked `train`, `validation`, and `test` assignments; never regenerate or infer a split by row position.
- Fit imputers, encoder state, and Track B scaling only on training rows; validation/test are transform-only.
- Return fresh, unfitted sklearn-compatible factory products suitable for fold-local cloning and fitting.
- Emit exact indicator names `tumor_size_was_missing` and `er_status_measured_by_ihc_was_missing` from original pre-imputation values.
- Normalize Track C labels separately from X; exclude `NC` only through Track C eligibility.
- Include exactly 489 canonically ordered mRNA predictors in Tracks B and C and zero mutation predictors in every R4 task.
- Fail before model consumption if IDs, targets, split data, mutation annotations, or eligibility metadata reach final feature names.
- Do not implement or install any model, C-index, prediction, feature selection, mutation Track D, or clinical-decision behavior.
- Stop at the R4 increment gate.

---

### Task 1: Add preprocessing contracts and promote runtime dependencies

**Files:**
- Create: `src/contracts/preprocessing.py`
- Modify: `src/contracts/__init__.py`
- Modify: `pyproject.toml`
- Modify: `requirements.txt`
- Create: `tests/test_preprocessing_contracts.py`

**Interfaces:**
- Produces: `PreprocessingTask`, `PreprocessingTrack`, `EligibilityReasonCode`, `ExclusionCount`, `EligibilityResult`, `PreprocessingMetadata`.
- `EligibilityResult(mask: tuple[bool, ...], reasons: tuple[tuple[EligibilityReasonCode, ...], ...])` validates aligned lengths and exposes aggregate exclusion counts without patient identifiers.
- `PreprocessingMetadata` serializes ordered feature and policy tuples without pandas or sklearn types.

- [x] **Step 1: Write failing contract tests** for stable enum values, aligned masks/reasons, aggregate exclusion counts, serialization, invalid counts, exact policy fields, and absence of patient IDs.

```python
def test_eligibility_contract_aggregates_stable_reason_codes() -> None:
    result = EligibilityResult(
        mask=(True, False),
        reasons=((), (EligibilityReasonCode.NON_POSITIVE_SURVIVAL_DURATION,)),
    )
    assert result.excluded_count == 1
    assert result.exclusion_counts == (
        ExclusionCount(EligibilityReasonCode.NON_POSITIVE_SURVIVAL_DURATION, 1),
    )
```

- [x] **Step 2: Run `python -m pytest tests/test_preprocessing_contracts.py -q` and confirm import failure.**
- [x] **Step 3: Implement validated frozen contracts and exports; promote `numpy`, `pandas`, and `scikit-learn` to project/runtime requirements.**
- [x] **Step 4: Re-run the focused contract tests and confirm pass.**
- [x] **Step 5: Commit the independently green contract/dependency slice.**

### Task 2: Implement immutable metadata loading and task eligibility

**Files:**
- Create: `src/preprocessing/__init__.py`
- Create: `src/preprocessing/schema.py`
- Create: `src/preprocessing/eligibility.py`
- Create: `tests/test_preprocessing_eligibility.py`

**Interfaces:**
- `load_preprocessing_schema(paths: MetabricPaths | None = None) -> PreprocessingSchema`
- `evaluate_clinical_survival_eligibility(prepared: pd.DataFrame, manifest: pd.DataFrame) -> EligibilityResult`
- `evaluate_clinical_mrna_survival_eligibility(prepared: pd.DataFrame, manifest: pd.DataFrame, schema: PreprocessingSchema) -> EligibilityResult`
- `evaluate_subtype_eligibility(prepared: pd.DataFrame, manifest: pd.DataFrame, schema: PreprocessingSchema) -> EligibilityResult`
- `normalize_subtype_target(prepared: pd.DataFrame, schema: PreprocessingSchema) -> pd.Series`

- [x] **Step 1: Write synthetic failing eligibility tests** proving positive-duration/event rules, exact zero-duration reason, missing and invalid target reasons, locked-split validation, mRNA numeric/finite requirements, NC independence for A/B, NC exclusion for C, zero-duration independence for C, and source-to-canonical subtype mapping.

```python
def test_zero_duration_affects_only_survival_tasks() -> None:
    survival = evaluate_clinical_survival_eligibility(prepared, manifest)
    subtype = evaluate_subtype_eligibility(prepared, manifest, schema)
    assert survival.mask == (False,)
    assert survival.reasons[0] == (EligibilityReasonCode.NON_POSITIVE_SURVIVAL_DURATION,)
    assert subtype.mask == (True,)
```

- [x] **Step 2: Run the eligibility tests and confirm they fail because the package is absent.**
- [x] **Step 3: Implement strict JSON metadata loading, one-to-one patient-ID alignment, independent task rules, row-aligned reasons, and separate subtype target normalization.**
- [x] **Step 4: Re-run eligibility and existing R2/R3 tests; confirm all pass.**
- [x] **Step 5: Commit the independently green eligibility slice.**

### Task 3: Implement exact clinical preprocessing and Track A factory

**Files:**
- Create: `src/preprocessing/clinical.py`
- Create: `src/preprocessing/pipelines.py`
- Create: `tests/test_preprocessing_pipelines.py`

**Interfaces:**
- `OriginalMissingIndicator(feature_name: str, output_name: str)` is sklearn cloneable and exposes `get_feature_names_out()` with the exact contractual output name.
- `build_clinical_survival_preprocessor(schema: PreprocessingSchema) -> Pipeline`
- `get_transformed_feature_names(preprocessor: Pipeline) -> tuple[str, ...]`
- `assert_safe_feature_names(feature_names: tuple[str, ...]) -> None`

- [x] **Step 1: Write failing tests** for train-only tumor median, train-only ER mode, exact original-value indicator names/values, accepted `Unknown` stage, ignored unseen categories, no Track A scaling, cloneability, deterministic output, and forbidden-name rejection.

```python
def test_missing_indicators_use_original_values_and_exact_names(schema) -> None:
    pipeline = build_clinical_survival_preprocessor(schema)
    transformed = pipeline.fit_transform(train_frame)
    names = get_transformed_feature_names(pipeline)
    assert "tumor_size_was_missing" in names
    assert "er_status_measured_by_ihc_was_missing" in names
    assert transformed[missing_row, names.index("tumor_size_was_missing")] == 1
```

- [x] **Step 2: Run the focused pipeline tests and confirm the factory/import failures.**
- [x] **Step 3: Implement the minimal cloneable indicator, schema guard, deterministic clinical `ColumnTransformer`, explicit schema categories, and Track A factory.**
- [x] **Step 4: Run the focused tests, refactor only while green, and run contract/eligibility regression tests.**
- [x] **Step 5: Commit the independently green Track A slice.**

### Task 4: Implement Tracks B/C, task feature selection, and fitted metadata

**Files:**
- Modify: `src/preprocessing/pipelines.py`
- Create: `src/preprocessing/metabric.py`
- Modify: `src/preprocessing/__init__.py`
- Modify: `tests/test_preprocessing_pipelines.py`
- Create: `tests/test_preprocessing_integration.py`

**Interfaces:**
- `build_clinical_mrna_survival_preprocessor(schema: PreprocessingSchema) -> Pipeline`
- `build_subtype_preprocessor(schema: PreprocessingSchema) -> Pipeline`
- `select_task_features(prepared: pd.DataFrame, task: PreprocessingTask, schema: PreprocessingSchema) -> pd.DataFrame`
- `build_preprocessing_metadata(task, schema, eligibility, fitted_preprocessor, fitted_on_split="train") -> PreprocessingMetadata`
- `verify_canonical_preprocessing(paths: MetabricPaths | None = None) -> CanonicalPreprocessingReport`

- [x] **Step 1: Write failing tests** for exact 489-gene inclusion/order, train-only Track B scaler state, transform-only state stability, Track C identity behavior, target exclusion from X, zero mutation fields, deterministic feature names, cloneability, and leakage guard failure.
- [x] **Step 2: Write a failing canonical integration test** asserting R2/R3 gates, aggregate task counts, missingness counts, transformed counts, zero mutation features, zero forbidden names, and immutable artifact hashes before/after verification.
- [x] **Step 3: Run focused tests and confirm failures for the missing factories/service.**
- [x] **Step 4: Implement Tracks B/C, explicit ordered feature selectors, fitted metadata extraction, and read-only canonical verification that fits only eligible training rows and transforms holdouts.**
- [x] **Step 5: Run focused integration tests and existing R2/R3 regressions; confirm pass.**
- [x] **Step 6: Commit the independently green Track B/C and integration slice.**

### Task 5: Document R4 architecture and boundaries

**Files:**
- Create: `docs/preprocessing.md`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/architecture.md`
- Modify: `docs/data.md`
- Modify: `docs/api_contracts.md`
- Modify: `docs/testing.md`
- Modify: `docs/limitations.md`
- Modify: `docs/model_integration.md`
- Modify: `docs/model_training.md`
- Modify: `docs/implementation_log.md`
- Modify: `docs/user_flow.md`

**Interfaces:** Human-facing documentation reflects implemented behavior only and reports no model metrics.

- [x] **Step 1: Document** the three task factories, training-only fit policy, future fold-local CV architecture, exact indicators, eligibility and reason codes, zero-duration/NC separation, deterministic ordering, Track B scaler, Track C no-scaler policy, mutation deferment, leakage guard, dependency boundary, and R4/R5/R6/R7 separation.
- [x] **Step 2: Record actual canonical counts produced by the implementation, with no patient-level records or fabricated model results.**
- [x] **Step 3: Run documentation-facing regression tests and review terminology for the frozen Track names.**
- [x] **Step 4: Commit the documentation slice.**

### Task 6: Complete fresh R4 verification and gate review

**Files:**
- Modify only if verification exposes a tested defect.

**Interfaces:** The final report is derived from fresh commands and the canonical report contract.

- [x] **Step 1: Run focused R4 tests:** `python -m pytest tests/test_preprocessing_contracts.py tests/test_preprocessing_eligibility.py tests/test_preprocessing_pipelines.py tests/test_preprocessing_integration.py -q`.
- [x] **Step 2: Run full regression:** `python -m pytest`.
- [x] **Step 3: Run compile check:** `python -m compileall app.py src tests scripts`.
- [x] **Step 4: Run dependency checks:** import NumPy/pandas/sklearn/Streamlit and run `python -m pip check`.
- [x] **Step 5: Run canonical preprocessing smoke verification** and print Track A/B/C counts, exclusions, indicator counts, raw/transformed feature counts, 489-gene checks, mutation count, forbidden count, and fitted-state invariance.
- [x] **Step 6: Verify canonical raw/prepared SHA-256 values are unchanged and inspect `git diff --check`, `git diff --stat`, and `git status --short` while preserving unrelated `ai_handoff_data/`.**
- [x] **Step 7: If active Streamlit code changed, start Streamlit headlessly, confirm HTTP health, and stop it; otherwise record that UI behavior was unchanged.**
- [x] **Step 8: Update this plan's checkboxes, commit final verification/documentation corrections if any, and stop at the R4 gate without beginning model work.**
