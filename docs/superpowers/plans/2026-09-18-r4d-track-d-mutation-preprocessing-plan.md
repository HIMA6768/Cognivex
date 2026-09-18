# R4D Track D Mutation Preprocessing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add cloneable, fit-local clinical-plus-mutation survival preprocessing for Track D without fitting a model or changing Tracks A–C.

**Architecture:** A shared mutation parser feeds row eligibility, a fit-local mutation-frequency selector, and an all-173-gene burden transformer. A Track-D-specific `ColumnTransformer` composes standardized continuous clinical variables, unscaled clinical binary indicators, unscaled fit-selected mutation indicators, and standardized log1p burden; canonical verification fits this complete object only on the locked training partition.

**Tech Stack:** Python 3.11+, dataclasses, pandas, NumPy, scikit-learn, pytest, Streamlit.

**Spec:** `docs/superpowers/specs/2026-09-18-r4d-track-d-mutation-preprocessing-design.md`

## Global Constraints

- Keep subagents off and execute in the current parent session.
- Preserve all pre-existing dirty R4 cleanup and R4D-P0 changes; never stage or discard `ai_handoff_data/`.
- Require R2 `DATA_READY` and a non-blocked R3 quality report before canonical Track D verification.
- Never rewrite canonical raw, prepared, manifest, mapping, schema, subtype, provenance, checksum, or R4D-P0 result artifacts.
- Freeze the task identifier as `clinical_mutation_survival`, the track as `Track D`, and the inclusive prevalence threshold as `>= 0.05`.
- Learn retained mutation genes only from each call to `fit()`; never hardcode the canonical 27-gene evidence list.
- Treat the canonical 27 retained genes and 44 transformed features only as integration evidence.
- Compute burden across all 173 mutation source fields and emit only `mutation_burden_log1p`.
- Standardize only Track D continuous clinical predictors and log1p burden; leave one-hot, missing-indicator, and mutation-presence features unscaled.
- Metadata must explicitly and exhaustively identify Track D standardized continuous versus unscaled binary/one-hot final features.
- Preserve exact missing-indicator names `tumor_size_was_missing` and `er_status_measured_by_ihc_was_missing`.
- Keep `NC` independent of Track D eligibility and preserve `NON_POSITIVE_SURVIVAL_DURATION` for the zero-duration row.
- Keep Track B mutation-free and preserve all Track A/B/C behavior.
- Do not fit a survival model, calculate C-index, tune hyperparameters, rank outcome-associated genes, or begin R5/R6/R7/R8.

---

### Task 1: Extend framework-independent Track D contracts

**Files:**
- Modify: `src/contracts/preprocessing.py`
- Modify: `src/contracts/__init__.py`
- Modify: `tests/test_preprocessing_contracts.py`

**Interfaces:**
- Produces `PreprocessingTask.CLINICAL_MUTATION_SURVIVAL` and `PreprocessingTrack.TRACK_D`.
- Produces `EligibilityReasonCode.MISSING_MUTATION_VALUE` and `EligibilityReasonCode.INVALID_MUTATION_VALUE`.
- Produces `MutationFeatureSelection`, `MutationSelectionMetadata`, and `MutationPreprocessingMetadata` serializable dataclasses.
- Extends `PreprocessingMetadata` with optional Track D mutation metadata plus `standardized_continuous_feature_names` and `unscaled_binary_feature_names`.

- [ ] **Step 1: Write failing contract tests.**

Add literal construction and serialization tests proving stable Track D enum values, inclusive threshold metadata, ordered raw-to-gene-to-derived mappings, retained/excluded derivation, and the two final scaling groups. Add invalid-contract tests proving Track D rejects missing mutation metadata, overlapping groups, groups that do not exactly partition final features, or noncanonical derived names.

```python
selection = MutationSelectionMetadata(
    threshold=0.05,
    comparison="greater_than_or_equal",
    fit_row_count=20,
    features=(
        MutationFeatureSelection("gene_a_mut", "gene_a", "gene_a_mut_present", 0.05, True),
        MutationFeatureSelection("gene_b_mut", "gene_b", "gene_b_mut_present", 0.0, False),
    ),
)
assert selection.retained_feature_names == ("gene_a_mut_present",)
assert selection.excluded_genes == ("gene_b",)
```

- [ ] **Step 2: Run `\.venv\Scripts\python.exe -m pytest tests/test_preprocessing_contracts.py -q` and confirm RED because Track D contract symbols are absent.**
- [ ] **Step 3: Implement the minimum validated enums and dataclasses.** Keep defaults backward-compatible for A/B/C metadata constructors, but require complete mutation and scaling-group metadata whenever the task is Track D.
- [ ] **Step 4: Re-run the contract tests and existing contract suite; refactor validation only while green.**
- [ ] **Step 5: Record the green checkpoint without staging unrelated pre-existing changes.**

### Task 2: Implement shared mutation semantics, fit-local selection, and burden

**Files:**
- Create: `src/preprocessing/mutations.py`
- Modify: `src/data/mutation_profile.py`
- Modify: `src/preprocessing/__init__.py`
- Create: `tests/test_mutation_preprocessing.py`
- Modify: `tests/test_mutation_profile.py`

**Interfaces:**
- `classify_mutation_annotation(value: object) -> tuple[MutationAnnotationKind, str | None]`
- `MutationFrequencySelector(mutation_columns: tuple[str, ...], min_prevalence: float = 0.05)`
- `MutationBurdenTransformer(mutation_columns: tuple[str, ...])`
- Selector fitted attributes include ordered source names, fit-row count, per-gene prevalence, retained/excluded names, and deterministic output names.

- [ ] **Step 1: Write failing parser tests.**

Use literal values to prove trimmed `"0"` and numeric zero are absent, annotation strings and finite nonzero numbers are present, blank/null are missing, and bool/non-finite values fail. The production mutation that these tests catch is silently treating raw annotation identity or malformed values as numeric magnitude.

```python
assert classify_mutation_annotation(" 0 ")[0] is MutationAnnotationKind.ABSENT
assert classify_mutation_annotation("H1047R")[0] is MutationAnnotationKind.PRESENT
with pytest.raises(ValueError, match="non-finite"):
    classify_mutation_annotation(float("inf"))
```

- [ ] **Step 2: Run the parser tests and confirm RED due to the missing module.**
- [ ] **Step 3: Implement only the pure parser and update R4D-P0 to consume it without changing profile outputs.**
- [ ] **Step 4: Run parser and R4D-P0 tests; confirm green and unchanged profiling facts.**
- [ ] **Step 5: Write failing selector tests.**

Use 20-row synthetic frames so one gene has 2/20, one has exactly 1/20, and one has 0/20 mutations. Verify inclusive retention, canonical input order, validation values cannot change fitted selection, separately fitted folds can select different genes, malformed/missing values fail, and `sklearn.base.clone` succeeds.

```python
selector.fit(train)
assert selector.get_feature_names_out().tolist() == ["above_mut_present", "boundary_mut_present"]
selector.transform(validation_with_different_prevalence)
assert selector.get_feature_names_out().tolist() == ["above_mut_present", "boundary_mut_present"]
```

- [ ] **Step 6: Run selector tests and confirm RED because `MutationFrequencySelector` is absent.**
- [ ] **Step 7: Implement the minimum sklearn-compatible selector.** Validate exact ordered inputs, derive binary values, compute means on fit rows, retain with `>=`, store fitted evidence, and output only fitted columns during transform.
- [ ] **Step 8: Run selector tests and confirm green.**
- [ ] **Step 9: Write failing burden tests.** Prove burden uses every declared source gene rather than selected genes, zero maps to `0.0`, a known count maps to the hand-derived `np.log1p(count)`, and all-mutated rows handle the declared maximum.
- [ ] **Step 10: Run burden tests and confirm RED because `MutationBurdenTransformer` is absent.**
- [ ] **Step 11: Implement the deterministic cloneable burden transformer with one output name, `mutation_burden_log1p`.**
- [ ] **Step 12: Re-run all mutation preprocessing and profiling tests; refactor shared frame validation only while green.**
- [ ] **Step 13: Record the green checkpoint without replacing the committed profiling artifacts.**

### Task 3: Add Track D eligibility without changing existing tasks

**Files:**
- Modify: `src/preprocessing/eligibility.py`
- Modify: `src/preprocessing/__init__.py`
- Modify: `tests/test_preprocessing_eligibility.py`

**Interfaces:**
- `evaluate_clinical_mutation_survival_eligibility(prepared: pd.DataFrame, manifest: pd.DataFrame, schema: PreprocessingSchema) -> EligibilityResult`
- Consumes the shared mutation parser and existing survival eligibility result.

- [ ] **Step 1: Write failing eligibility tests.** Prove valid `NC` remains eligible, zero duration yields `NON_POSITIVE_SURVIVAL_DURATION`, missing tumor size/ER-IHC remains eligible, invalid event is excluded, blank mutation values yield `MISSING_MUTATION_VALUE`, malformed mutation values yield `INVALID_MUTATION_VALUE`, and changing mutation prevalence does not affect eligibility.

```python
result = evaluate_clinical_mutation_survival_eligibility(
    prepared.assign(**{"pam50_+_claudin-low_subtype": "NC"}), manifest, schema
)
assert result.mask == (True,)
```

- [ ] **Step 2: Run focused eligibility tests and confirm RED because the Track D evaluator is absent.**
- [ ] **Step 3: Implement Track D eligibility by composing existing survival reasons with row-level mutation structural reasons.** Required-column absence remains a fail-loud dataset error; row-level blank/null and malformed values receive stable reason codes.
- [ ] **Step 4: Run all preprocessing eligibility tests and confirm A/B/C expectations remain green.**
- [ ] **Step 5: Record the green checkpoint.**

### Task 4: Build the scaled Track D preprocessor and fitted metadata

**Files:**
- Modify: `src/preprocessing/pipelines.py`
- Modify: `src/preprocessing/__init__.py`
- Modify: `tests/test_preprocessing_pipelines.py`
- Modify: `tests/test_mutation_preprocessing.py`

**Interfaces:**
- `build_clinical_mutation_survival_preprocessor(schema: PreprocessingSchema) -> Pipeline`
- `select_task_features(..., PreprocessingTask.CLINICAL_MUTATION_SURVIVAL, schema)` returns seven clinical plus 173 mutation source fields.
- `build_preprocessing_metadata(...)` emits Track D nested selector/burden metadata and exact standardized/unscaled groups.

- [ ] **Step 1: Write failing Track D factory tests.**

Build a synthetic schema/frame and assert the desired public output order: the established 16 clinical names, fit-selected `*_mut_present` names in source order, then `mutation_burden_log1p`. Assert the factory is fresh, initially unfitted, cloneable, deterministic, and does not mutate source frames.

- [ ] **Step 2: Write failing scaling-separation tests.** Fit on hand-derived continuous values and assert the four continuous outputs have train-fit scaler behavior while every one-hot, missing indicator, and mutation-presence output remains exactly binary. Transform extreme holdout values and prove fitted means/scales and selected genes do not change.

```python
metadata = build_preprocessing_metadata(...)
assert metadata.standardized_continuous_feature_names == (
    "age_at_diagnosis",
    "tumor_size",
    "lymph_nodes_examined_positive",
    "mutation_burden_log1p",
)
assert set(metadata.standardized_continuous_feature_names).isdisjoint(
    metadata.unscaled_binary_feature_names
)
assert set(metadata.standardized_continuous_feature_names + metadata.unscaled_binary_feature_names) == set(
    metadata.final_feature_names
)
```

- [ ] **Step 3: Run focused pipeline tests and confirm RED for the missing factory/task mapping.**
- [ ] **Step 4: Refactor the existing clinical column construction behind one private builder with a Track-D-only continuous-scaling option.** Preserve Track A branch names and fitted-object paths used by existing tests; do not change Track B or C factories.
- [ ] **Step 5: Implement the outer guarded Track D `ColumnTransformer` with clinical, selector, and burden-plus-scaler branches.**
- [ ] **Step 6: Extend task feature selection, leakage checks, and metadata extraction.** Raw `*_mut` names remain forbidden in final X; derived `*_mut_present` names are allowed only as selector outputs.
- [ ] **Step 7: Run all pipeline, contract, mutation, and eligibility tests; confirm green.**
- [ ] **Step 8: Run explicit A/B/C regression assertions and prove Track B has zero `*_mut_present` outputs.**
- [ ] **Step 9: Record the green checkpoint.**

### Task 5: Extend canonical verification and aggregate readiness UI

**Files:**
- Modify: `src/preprocessing/metabric.py`
- Modify: `src/ui/pages/data_cohort.py`
- Modify: `tests/test_preprocessing_integration.py`
- Modify: `tests/test_app_shell.py`

**Interfaces:**
- `verify_canonical_preprocessing()` returns A/B/C/D metadata in enum order.
- Canonical Track D metadata exposes selector evidence, feature scaling groups, eligibility counts, and immutable hashes.
- The Data / Cohort page renders aggregate Track D readiness only from that report.

- [ ] **Step 1: Write a failing canonical integration test.** Assert Track D eligibility is 1,332 train, 285 validation, 286 test, and 1,903 total; source mutation count is 173; threshold is `0.05`; the current full-training fit retains 27 genes; transformed count is 44; and standardized/unscaled metadata partitions all 44 names.
- [ ] **Step 2: Add a failing evidence comparison test.** Read `results/mutation_profile_train.csv` and prove the selector's full-training retained raw columns equal rows with `retain_ge_5pct == True`; do not load that result file in application runtime.
- [ ] **Step 3: Add failing isolation and immutability assertions.** Track A/B/C counts and output orders remain unchanged, Track B has zero mutation predictors, raw/prepared hashes are unchanged, and validation/test transforms leave fitted Track D state unchanged.
- [ ] **Step 4: Run focused integration tests and confirm RED because canonical verification has no Track D task.**
- [ ] **Step 5: Extend canonical mappings, fit/transform flow, and aggregate report population for Track D.** Keep 27 and 44 only in test assertions and reported evidence, never runtime control flow.
- [ ] **Step 6: Run focused canonical tests and confirm green.**
- [ ] **Step 7: Write a failing Streamlit test for four aggregate readiness cards and Track D copy without patient-level mutation values.**
- [ ] **Step 8: Run the focused app test and confirm RED because only A–C are rendered.**
- [ ] **Step 9: Update the Data / Cohort page to use four columns, A–D readiness copy, and contract-derived Track D aggregate counts.** Keep the research disclaimer and aggregate-only boundary.
- [ ] **Step 10: Re-run Streamlit tests and the complete focused R4D/R4 set.**
- [ ] **Step 11: Record the green checkpoint.**

### Task 6: Document Track D and future model boundary

**Files:**
- Create: `docs/mutation_preprocessing.md`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/architecture.md`
- Modify: `docs/data.md`
- Modify: `docs/api_contracts.md`
- Modify: `docs/preprocessing.md`
- Modify: `docs/testing.md`
- Modify: `docs/limitations.md`
- Modify: `docs/model_integration.md`
- Modify: `docs/model_training.md`
- Modify: `docs/implementation_log.md`
- Modify: `docs/user_flow.md`

**Interfaces:** Human-facing documentation reports implemented preprocessing evidence only and no model result.

- [ ] **Step 1: Document** Track D purpose, 173 source annotations, shared binary semantics, missing/malformed policy, inclusive fit-local 5% selector, fold-varying retained sets, deterministic names/order, and the evidence-versus-constant boundary.
- [ ] **Step 2: Document** all-173-gene burden, `log1p`, explicit standardized continuous group, explicit unscaled binary/one-hot group, clinical policy reuse, Track D eligibility, NC independence, zero-duration handling, and forbidden predictors.
- [ ] **Step 3: Record canonical evidence** only after the integration test supplies actual counts: eligibility by split, 27 retained genes, 16+27+1=44 composition, and Track B zero mutations. Label 27 and 44 as current locked-training evidence, never production constants.
- [ ] **Step 4: Document future modeling only:** penalized Cox, same-eligible-population A/B/D comparison, and complete preprocessor-plus-selector-plus-model placement inside CV. Do not add model code or metrics.
- [ ] **Step 5: Review all changed prose for research-only language and confirm no patient-level values or fabricated scientific results appear.**
- [ ] **Step 6: Record the documentation checkpoint while preserving pre-existing overlapping documentation changes.**

### Task 7: Complete fresh R4D verification and stop at the gate

**Files:**
- Modify only if verification exposes a defect reproduced by a new failing test.

**Interfaces:** Final gate evidence is taken from fresh command output, not prior runs.

- [ ] **Step 1: Run focused R4D tests:**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_mutation_preprocessing.py tests/test_preprocessing_contracts.py tests/test_preprocessing_eligibility.py tests/test_preprocessing_pipelines.py tests/test_preprocessing_integration.py -q
```

- [ ] **Step 2: Run existing R4 and R4D-P0 tests:**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_mutation_profile.py tests/test_preprocessing_contracts.py tests/test_preprocessing_eligibility.py tests/test_preprocessing_pipelines.py tests/test_preprocessing_integration.py -q
```

- [ ] **Step 3: Run the full regression suite exactly once after focused verification:**

```powershell
.\.venv\Scripts\python.exe -m pytest
```

- [ ] **Step 4: Run compile and dependency checks:**

```powershell
.\.venv\Scripts\python.exe -m compileall app.py src tests scripts
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -c "import numpy, pandas, sklearn, streamlit"
```

- [ ] **Step 5: Run a canonical Track D smoke script** that prints eligibility by split, exclusion reasons, 173 source fields, threshold `0.05`, fitted retained count/names, burden policy, 16/retained/1/total composition, standardized/unscaled groups, Track B mutation count, forbidden-name count, and fitted-state invariance.
- [ ] **Step 6: Verify cloneability and deterministic repeated fits on canonical eligible training rows.**
- [ ] **Step 7: Recompute SHA-256 for raw/prepared data before and after verification and compare against the canonical report.**
- [ ] **Step 8: Start Streamlit headlessly, poll its health endpoint, and stop it; then perform desktop and narrow-layout browser checks plus console inspection because readiness UI changed.**
- [ ] **Step 9: Run `git diff --check`, inspect `git diff --stat`, and run `git status --short`; confirm `ai_handoff_data/` remains untouched.**
- [ ] **Step 10: Re-read the specification and this plan, verify every requirement against code/tests/docs, and stop at the R4D gate without fitting a model.**
