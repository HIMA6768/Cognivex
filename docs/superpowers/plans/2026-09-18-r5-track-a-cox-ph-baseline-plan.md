# R5 Track A Clinical-Only Cox PH Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fit and evaluate a leak-safe, unpenalized clinical-only Cox PH baseline on locked METABRIC train/validation partitions while leaving test untouched.

**Architecture:** Reuse R4 feature selection, eligibility, and preprocessing; place lifelines behind a focused adapter; keep metrics, diagnostics, contracts, orchestration, and artifact persistence separate. An explicit CLI performs the canonical run, and Streamlit remains unchanged.

**Tech Stack:** Python 3.11+, pandas 2.3.3, NumPy 2.x, scikit-learn 1.x, lifelines 0.30.3, pytest.

**Spec:** `docs/superpowers/specs/2026-09-18-r5-track-a-cox-ph-baseline-design.md`

## Global Constraints

- Dependency gate first: `lifelines==0.30.3`, `pandas==2.3.3`, `pip check`, then all 140 pre-R5 tests.
- Stop on dependency regression or conflict; do not fit R5.
- Reuse the existing R4 Track A factory and eligibility unchanged.
- Fit train only; validation is transform/evaluate only; test is never transformed, predicted, or scored.
- Use unpenalized Breslow Cox PH with `alpha=0.05`; no fallback.
- Stop on material convergence warning/failure; preserve matrix and fit evidence.
- Keep binary pickle artifacts local and Git-ignored.
- Do not implement R6, Track C/D models, final test evaluation, or Streamlit results UI.

---

### Task 1: Freeze the specification and dependency compatibility gate

**Files:**
- Modify: `pyproject.toml`
- Modify: `requirements.txt`
- Test: complete existing suite

**Interfaces:**
- Consumes: current project virtual environment and pre-R5 regression baseline.
- Produces: resolved environment with pandas 2.3.3 and lifelines 0.30.3.

- [ ] **Step 1: Change only the approved constraints**

```toml
"lifelines==0.30.3",
"pandas==2.3.3",
```

- [ ] **Step 2: Install into `.venv` and verify integrity**

Run: `.venv\Scripts\python.exe -m pip install -e ".[dev]"`

Run: `.venv\Scripts\python.exe -m pip check`

Expected: dependency resolution succeeds and `pip check` reports no broken requirements.

- [ ] **Step 3: Verify exact resolved versions**

Run: `.venv\Scripts\python.exe -c "import lifelines,pandas; print(lifelines.__version__, pandas.__version__)"`

Expected: `0.30.3 2.3.3`.

- [ ] **Step 4: Run the complete pre-model regression gate**

Run: `.venv\Scripts\python.exe -m pytest`

Expected: all 140 pre-R5 tests pass. Stop otherwise.

### Task 2: Add immutable survival result contracts

**Files:**
- Create: `src/contracts/survival.py`
- Modify: `src/contracts/__init__.py`
- Create: `tests/test_survival_contracts.py`

**Interfaces:**
- Produces: `CoxModelConfiguration`, `SurvivalCohortSummary`, `MatrixDiagnostic`, `ConcordanceResult`, `CoefficientEstimate`, `PHFeatureDiagnostic`, `PHDiagnostics`, `RuntimeProvenance`, `ArtifactRecord`, and `TrackAExperimentResult`.

- [ ] **Step 1: Write failing construction, validation, and serialization tests**

```python
def test_track_a_result_serializes_nested_evidence() -> None:
    result = make_valid_track_a_result()
    payload = result.to_dict()
    assert payload["configuration"]["track"] == "track_a"
    assert payload["validation_metric"]["score_direction"] == "higher_risk_is_higher_hazard"

def test_concordance_rejects_out_of_range_values() -> None:
    with pytest.raises(ValueError):
        ConcordanceResult(..., c_index=1.01, ...)
```

- [ ] **Step 2: Run tests and verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_survival_contracts.py -v`

Expected: import failure because R5 contracts do not exist.

- [ ] **Step 3: Implement minimal frozen dataclasses and enums**

Use the repository's `SerializableContract` pattern. Validate non-empty strings, finite numeric values, ordered unique feature names, counts, statuses, C-index bounds, and nested contract types.

- [ ] **Step 4: Run focused contracts tests and verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/test_survival_contracts.py -v`

### Task 3: Implement metric direction and matrix diagnostics test-first

**Files:**
- Create: `src/evaluation/__init__.py`
- Create: `src/evaluation/survival.py`
- Create: `tests/test_survival_evaluation.py`

**Interfaces:**
- Produces: `harrell_c_index(durations, events, risk_scores, *, split, cohort_fingerprint) -> ConcordanceResult`.
- Produces: `diagnose_design_matrix(values, feature_names) -> MatrixDiagnostic`.

- [ ] **Step 1: Write failing literal synthetic metric tests**

```python
def test_higher_risk_for_earlier_event_is_perfect() -> None:
    result = harrell_c_index([1, 2, 3], [1, 1, 1], [3, 2, 1], split="synthetic", cohort_fingerprint="a" * 64)
    assert result.c_index == 1.0

def test_reversed_risk_is_anti_concordant() -> None:
    result = harrell_c_index([1, 2, 3], [1, 1, 1], [1, 2, 3], split="synthetic", cohort_fingerprint="a" * 64)
    assert result.c_index == 0.0
```

Add independent tied-score and censoring fixtures with hand-derived expected values.

- [ ] **Step 2: Run metric tests and verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_survival_evaluation.py -v`

- [ ] **Step 3: Implement the approved score direction**

```python
score = concordance_index(durations, -np.asarray(risk_scores), events)
```

- [ ] **Step 4: Write failing matrix evidence tests**

Use literal matrices proving full rank, duplicate columns, zero variance, and exact rank deficiency.

- [ ] **Step 5: Implement deterministic matrix diagnostics**

Use `numpy.linalg.matrix_rank`, exact array equality for duplicates, zero peak-to-peak values, finite checks, and deterministic null-space/dependency evidence derived from SVD.

- [ ] **Step 6: Run focused tests and verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/test_survival_evaluation.py -v`

### Task 4: Implement the lifelines adapter and PH diagnostics test-first

**Files:**
- Create: `src/modeling/__init__.py`
- Create: `src/modeling/survival.py`
- Create: `tests/test_survival_modeling.py`

**Interfaces:**
- Produces: `LifelinesCoxPHAdapter.fit(X, durations, events, feature_names) -> None`.
- Produces: `predict_risk(X) -> numpy.ndarray`.
- Produces: `coefficient_estimates() -> tuple[CoefficientEstimate, ...]`.
- Produces: `evaluate_ph_assumptions() -> PHDiagnostics`.

- [ ] **Step 1: Write failing adapter configuration and target-isolation tests**

Assert the exact approved fitter configuration and prove duration/event names are absent from adapter feature names.

- [ ] **Step 2: Run adapter tests and verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_survival_modeling.py -v`

- [ ] **Step 3: Implement the minimal adapter**

Construct the approved `CoxPHFitter`, create a private fit frame with reserved `__duration` and `__event` columns, capture `ConvergenceWarning`, and reject material warnings by raising a typed `CoxFitError` carrying preserved evidence.

- [ ] **Step 4: Add failing coefficient and diagnostic tests**

Fit a small deterministic synthetic survival fixture and assert ordered names, `exp(coef)`, 95% intervals, p-values, rank-transform diagnostic rows, and explicit diagnostic failure status.

- [ ] **Step 5: Implement coefficient extraction and PH diagnostics**

Read `CoxPHFitter.summary`; call `proportional_hazard_test(..., time_transform="rank")`; never mutate the model or feature set from diagnostic flags.

- [ ] **Step 6: Run focused adapter tests and verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/test_survival_modeling.py -v`

### Task 5: Implement trusted local artifacts test-first

**Files:**
- Create: `src/artifacts/__init__.py`
- Create: `src/artifacts/survival.py`
- Modify: `.gitignore`
- Create: `tests/test_survival_artifacts.py`

**Interfaces:**
- Produces: `write_track_a_artifacts(bundle, result, output_root) -> tuple[ArtifactRecord, ...]`.
- Produces: explicit trusted loaders requiring `trusted=True` for pickle deserialization.

- [ ] **Step 1: Write failing bundle and trust-boundary tests**

Verify exact filenames, SHA-256 manifest coverage, stable JSON, CSV headers, ignored pickle paths, and refusal to load pickle without explicit trust.

- [ ] **Step 2: Run artifact tests and verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_survival_artifacts.py -v`

- [ ] **Step 3: Implement deterministic artifact writing**

Write JSON with sorted keys and newline termination, CSVs in feature order, pickle objects locally, and `checksums.sha256` for every file except itself. Reject existing non-empty experiment directories to avoid accidental overwrite.

- [ ] **Step 4: Git-ignore trusted binary artifacts**

Ignore `artifacts/models/**/preprocessor.pkl` and `artifacts/models/**/cox_model.pkl` while allowing JSON/CSV/checksum evidence.

- [ ] **Step 5: Run artifact tests and verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/test_survival_artifacts.py -v`

### Task 6: Implement Track A orchestration test-first

**Files:**
- Create: `src/training/__init__.py`
- Create: `src/training/track_a.py`
- Create: `tests/test_track_a_training.py`

**Interfaces:**
- Produces: `prepare_track_a_run(paths) -> PreparedTrackARun` containing train/validation data only and aggregate held-out test metadata.
- Produces: `fit_track_a(prepared_run, experiment_id) -> FittedTrackABundle`.
- Produces: `evaluate_track_a_subset(bundle, raw_predictors, durations, events, patient_ids, split) -> ConcordanceResult`.

- [ ] **Step 1: Write failing split-boundary and leakage tests**

Use controlled synthetic prepared/manifest frames. Prove train is the only fit input, validation is transform-only, test never reaches `transform` or `predict`, targets remain separate, and forbidden predictors fail loudly.

- [ ] **Step 2: Run orchestration tests and verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_track_a_training.py -v`

- [ ] **Step 3: Implement preparation and fit orchestration**

Call R2/R3 gates, existing R4 schema/eligibility/selector/factory, split by locked manifest, fit train-only, transform validation-only, run matrix diagnostics before Cox fitting, and stop on material fitting evidence.

- [ ] **Step 4: Add failing common-subset and determinism tests**

Prove supplied evaluation subsets use the stored preprocessor/model without refitting, produce the expected fingerprint/counts, and give equivalent outputs across identical runs within documented tolerance.

- [ ] **Step 5: Implement common-subset evaluation and provenance capture**

Keep patient IDs in memory only; hash their ordered values; publish aggregate counts and fingerprint only.

- [ ] **Step 6: Run focused orchestration tests and verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/test_track_a_training.py -v`

### Task 7: Add the explicit canonical CLI and canonical integration test

**Files:**
- Create: `scripts/train_track_a.py`
- Create: `tests/test_track_a_integration.py`

**Interfaces:**
- CLI: `.venv\Scripts\python.exe scripts/train_track_a.py --experiment-id <id> --output-root artifacts/models/track_a`.

- [ ] **Step 1: Write a failing canonical dry-run/integration test**

Assert R2/R3 readiness, 1,332/285/286 eligibility, 16 transformed features, approved model config, train/validation event and censor totals, and explicit `test_transformed=False`, `test_predicted=False`, `test_scored=False` evidence.

- [ ] **Step 2: Run integration test and verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_track_a_integration.py -v`

- [ ] **Step 3: Implement CLI argument validation and execution**

Require a filesystem-safe experiment ID, repository-relative default output root, and explicit failure exit code with preserved evidence. Do not run training on import or Streamlit startup.

- [ ] **Step 4: Run canonical R5 fit once**

Run: `.venv\Scripts\python.exe scripts/train_track_a.py --experiment-id r5-track-a-baseline-v1`

Expected: either a verified train/validation bundle or an approved stop-condition report with exact matrix/convergence evidence. Never apply a remedy automatically.

- [ ] **Step 5: Verify canonical integration GREEN when fitting succeeds**

Run: `.venv\Scripts\python.exe -m pytest tests/test_track_a_integration.py -v`

### Task 8: Document and verify the R5 gate

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/architecture.md`
- Modify: `docs/model_training.md`
- Modify: `docs/model_evaluation.md`
- Modify: `docs/model_integration.md`
- Modify: `docs/limitations.md`
- Modify: `docs/testing.md`
- Modify: `docs/implementation_log.md`
- Create: `docs/survival_baseline.md`

**Interfaces:**
- Produces: exact R5 methods, boundaries, measured canonical evidence, limitations, and reproduction instructions.

- [ ] **Step 1: Document only measured outputs from the canonical run**

Record package versions, cohort counts, event/censor counts, matrix evidence, convergence status, train/validation C-index, PH flags, artifact location, test-held-out policy, and research-only limitations. Do not invent results.

- [ ] **Step 2: Run focused R5 tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_survival_contracts.py tests/test_survival_evaluation.py tests/test_survival_modeling.py tests/test_survival_artifacts.py tests/test_track_a_training.py tests/test_track_a_integration.py -v`

- [ ] **Step 3: Run complete regression verification**

Run: `.venv\Scripts\python.exe -m pytest`

- [ ] **Step 4: Run compile, dependency, and diff checks**

Run: `.venv\Scripts\python.exe -m compileall app.py src scripts tests`

Run: `.venv\Scripts\python.exe -m pip check`

Run: `git diff --check`

- [ ] **Step 5: Verify repository boundaries**

Confirm canonical raw/prepared/manifest SHA-256 values are unchanged, binary pickle files are ignored, `ai_handoff_data/` is untouched, Streamlit pages are unchanged, and no held-out test metric exists.

- [ ] **Step 6: Stop at the R5 gate**

Report status, dependencies, canonical fit/evaluation evidence, diagnostics, artifacts, tests, documentation, risks, untouched test evidence, Git status, and the next recommended gated step. Do not start R6.

### Task 9: Add the Track-A-only reference encoder and comparison metadata

**Files:**
- Modify: `src/preprocessing/pipelines.py`
- Modify: `src/contracts/survival.py`
- Modify: `src/contracts/__init__.py`
- Modify: `tests/test_preprocessing_pipelines.py`
- Modify: `tests/test_survival_contracts.py`

**Interfaces:**
- `build_clinical_survival_preprocessor(schema)` emits Track A reference-coded features.
- Track B and Track D call the unchanged full-category clinical branch.
- `CategoricalFeatureComparison(raw_variable, category, reference_category, derived_feature_name)` records interpretation metadata.

- [ ] **Step 1: Write failing behavior tests**

```python
assert "tumor_stage_1" not in track_a_names
assert "tumor_stage_Unknown" in track_a_names
assert "er_status_measured_by_ihc_Negative" not in track_a_names
assert len(track_b_names) == 505
assert len(track_d_names) == 44
```

- [ ] **Step 2: Verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_preprocessing_pipelines.py tests/test_survival_contracts.py -q`

Expected: Track A still contains the four approved reference columns and comparison metadata is unavailable.

- [ ] **Step 3: Implement explicit fixed drops for Track A only**

Pass `drop=[reference]` to each Track A `OneHotEncoder`; preserve full-category encoding for the clinical branch consumed by Tracks B/D. Validate each reference against schema categories.

- [ ] **Step 4: Verify GREEN and track isolation**

Run: `.venv\Scripts\python.exe -m pytest tests/test_preprocessing_pipelines.py tests/test_preprocessing_integration.py tests/test_mutation_preprocessing.py tests/test_survival_contracts.py -q`

### Task 10: Require full rank and record soft-collinearity evidence

**Files:**
- Modify: `src/contracts/survival.py`
- Modify: `src/evaluation/survival.py`
- Modify: `src/training/track_a.py`
- Modify: `tests/test_survival_evaluation.py`
- Modify: `tests/test_track_a_training.py`

**Interfaces:**
- `MatrixDiagnostic.condition_number` records the numeric 2-norm condition number.
- `fit_track_a` raises `TrackAFitStopped` before Cox fitting whenever `rank != feature_count`.

- [ ] **Step 1: Write failing rank-gate and condition-number tests**

```python
diagnostic = diagnose_design_matrix(np.eye(3), ("a", "b", "c"))
assert diagnostic.condition_number == pytest.approx(1.0)

with pytest.raises(TrackAFitStopped, match="full column rank"):
    fit_track_a(rank_deficient_prepared_run, "rank-stop")
```

- [ ] **Step 2: Verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_survival_evaluation.py tests/test_track_a_training.py -q`

- [ ] **Step 3: Implement the diagnostic and pre-fit gate**

Use `numpy.linalg.cond` on the finite training matrix. Stop before constructing or fitting the Cox adapter when rank differs from feature count.

- [ ] **Step 4: Verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/test_survival_evaluation.py tests/test_track_a_training.py -q`

### Task 11: Retry canonical R5A and persist successful evidence

**Files:**
- Create: `scripts/train_track_a.py`
- Create: `tests/test_track_a_integration.py`
- Modify: `src/training/track_a.py`
- Modify: `src/artifacts/survival.py`

**Interfaces:**
- CLI writes `artifacts/models/track_a/<experiment_id>/` after a successful fit only.
- Public artifacts contain aggregate evidence and no patient identifiers.

- [ ] **Step 1: Write the failing canonical integration test**

Assert 1,332 train rows with 760 events, 285 validation rows, 286 held-out test rows, full rank, reference metadata, approved model configuration, and false test-use flags.

- [ ] **Step 2: Verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_track_a_integration.py -q`

- [ ] **Step 3: Implement the CLI and successful artifact path**

The CLI validates a filesystem-safe experiment ID, calls `prepare_track_a_run`, `fit_track_a`, and `write_track_a_artifacts`, and serializes stop evidence without applying a fallback.

- [ ] **Step 4: Run the canonical retry once**

Run: `.venv\Scripts\python.exe scripts/train_track_a.py --experiment-id r5a-track-a-baseline-v1`

Expected: successful bundle or immediate exact stop evidence. No second modeling change is authorized.

### Task 12: Complete R5A documentation and verification

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/architecture.md`
- Modify: `docs/model_training.md`
- Modify: `docs/model_evaluation.md`
- Modify: `docs/model_integration.md`
- Modify: `docs/limitations.md`
- Modify: `docs/testing.md`
- Modify: `docs/implementation_log.md`
- Create: `docs/survival_baseline.md`

**Interfaces:**
- Documents the historical failure and measured R5A outcome without test performance or clinical claims.

- [ ] **Step 1: Record only measured canonical evidence**

Include the original 16/rank-13 failure, fixed references, derived feature count, full-rank/condition evidence, train and validation C-index, Stage 4 coefficient evidence, PH flags, artifact policy, and untouched-test boundary.

- [ ] **Step 2: Run focused and track-isolation tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_survival_contracts.py tests/test_survival_evaluation.py tests/test_survival_modeling.py tests/test_survival_artifacts.py tests/test_track_a_training.py tests/test_track_a_integration.py tests/test_preprocessing_pipelines.py tests/test_preprocessing_integration.py tests/test_mutation_preprocessing.py -q`

- [ ] **Step 3: Run the complete verification gate**

Run: `.venv\Scripts\python.exe -m pytest`

Run: `.venv\Scripts\python.exe -m compileall -q app.py src scripts tests`

Run: `.venv\Scripts\python.exe -m pip check`

Run: `git diff --check`

- [ ] **Step 4: Verify immutable boundaries and stop**

Recalculate raw/prepared/manifest SHA-256 values, prove local pickle paths are ignored, confirm `ai_handoff_data/` and Streamlit pages are untouched, report R5A, and do not begin R6.
