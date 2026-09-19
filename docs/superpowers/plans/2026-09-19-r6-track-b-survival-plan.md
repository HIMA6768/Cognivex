# R6 Track B Clinical + Genomic Survival Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Train, evaluate, persist, and audit the leak-safe Track B clinical-plus-selected-genomic penalized Cox model without changing R5.

**Architecture:** A dedicated R6 feature/preprocessing boundary embeds the frozen R5 clinical transformer and adds selected expression scaling plus R4D mutation presence. A separate training boundary selects a penalized Cox candidate on validation only, finalizes once on test, compares against trusted frozen R5 artifacts, and persists aggregate evidence plus a 25-check audit.

**Tech Stack:** Python 3.14, pandas 2.3.3, NumPy 2.x, scikit-learn 1.9.1, lifelines 0.30.3, pytest 9.

**Spec:** `docs/superpowers/specs/2026-09-19-r6-track-b-survival-design.md`

## Global Constraints

- Active prepared data and locked 1,332/286/286 manifest remain authoritative and immutable.
- Prepared `overall_survival` is already event-observed; never invert it.
- R5 source and artifacts remain unchanged; trusted R5 pickles may be loaded only for comparison.
- Raw Track B is exactly 7 clinical + 50 expression + 18 mutation columns.
- Candidate selection uses validation only; test is transformed/scored only after freezing the winner.
- No engineer historical pickle is loaded; no R7/R8/UI/inference work.

## Review Focus

- A reordered or duplicate selected-feature file must fail before matrix construction.
- A boolean, blank, missing, or non-finite mutation annotation must fail instead of becoming present.
- A validation/test-only category must not refit or reorder clinical features.
- A candidate with the best test score but worse validation score must not win.
- Reloaded artifacts must reject a different feature order and reproduce winner risk scores.

---

### Task 1: Track B contracts and explicit preprocessing

**Files:**
- Create: `src/contracts/track_b.py`
- Create: `src/preprocessing/track_b.py`
- Modify: `src/contracts/__init__.py`
- Modify: `src/preprocessing/__init__.py`
- Test: `tests/test_track_b_preprocessing.py`

**Interfaces:**
- Consumes: `build_clinical_survival_preprocessor(schema)`, `classify_mutation_annotation(value)`, and `parse_selected_features(path)`.
- Produces: `load_track_b_feature_contract(root) -> TrackBFeatureContract`, `SelectedMutationPresenceTransformer`, `build_track_b_preprocessor(schema, contract) -> Pipeline`, and `track_b_feature_names(preprocessor) -> tuple[str, ...]`.

- [ ] **Step 1: Write failing feature-contract and preprocessing tests** proving exact 7/50/18/75 counts, exact allowlisting, 80 encoded outputs, frozen R5 clinical output equality, train-only expression scaling, stable order, binary mutation output, malformed-value failure, and immutable source frames.
- [ ] **Step 2: Run `python -m pytest tests/test_track_b_preprocessing.py -q`** and confirm failure because R6 types/modules do not exist.
- [ ] **Step 3: Implement immutable contracts, explicit list loading, the classifier-backed mutation transformer, and composite pipeline.** The mutation transformer may validate during `fit` but stores no learned encoding statistic.
- [ ] **Step 4: Re-run the focused test** and expect all Task 1 tests to pass.
- [ ] **Step 5: Commit** with `feat(r6): add Track B preprocessing and feature contract`.

### Task 2: Penalized model and validation-only selection

**Files:**
- Create: `src/modeling/track_b.py`
- Create: `src/training/track_b.py`
- Modify: `src/modeling/__init__.py`
- Modify: `src/training/__init__.py`
- Test: `tests/test_track_b_training.py`

**Interfaces:**
- Consumes: Task 1 feature contract/preprocessor and existing `harrell_c_index`/eligibility utilities.
- Produces: `prepare_track_b_run(paths) -> PreparedTrackBRun`, `select_track_b_candidate(prepared, candidates=TRACK_B_CANDIDATES, model_factory=...) -> SelectedTrackBModel`, and `finalize_track_b(selection, prepared, r5_artifact_root) -> TrackBExperimentResult`.

- [ ] **Step 1: Write failing tests** for event preservation, identical A/B eligibility, six-candidate grid, validation-only deterministic selection, candidate failure recording, no test access during selection, and one winner-only final test evaluation.
- [ ] **Step 2: Run `python -m pytest tests/test_track_b_training.py -q`** and confirm missing R6 training/model behavior.
- [ ] **Step 3: Implement the configurable Cox adapter and split training/finalization flow.** Test data cannot be accepted by candidate selection.
- [ ] **Step 4: Re-run the focused test** and expect all Task 2 tests to pass.
- [ ] **Step 5: Commit** with `feat(r6): add validation-selected penalized Cox training`.

### Task 3: Artifacts, reload, audit, and CLI

**Files:**
- Create: `src/artifacts/track_b.py`
- Create: `src/audit/__init__.py`
- Create: `src/audit/track_b.py`
- Create: `scripts/train_track_b.py`
- Modify: `src/artifacts/__init__.py`
- Modify: `.gitignore`
- Test: `tests/test_track_b_artifacts.py`
- Test: `tests/test_track_b_audit.py`

**Interfaces:**
- Consumes: finalized Task 2 experiment and fitted winner.
- Produces: `write_track_b_artifacts(...)`, `verify_track_b_reload(...)`, `audit_track_b(...)`, and the canonical CLI.

- [ ] **Step 1: Write failing tests** for non-overwriting persistence, trusted pickle reload, prediction reproduction, exact feature order, required JSON/CSV/report files, metric/report equality, ignored binaries, and all 25 audit checks.
- [ ] **Step 2: Run `python -m pytest tests/test_track_b_artifacts.py tests/test_track_b_audit.py -q`** and confirm missing persistence/audit behavior.
- [ ] **Step 3: Implement persistence, report rendering, reload verification, audit checks, and safe CLI validation.** Do not persist patient IDs or row predictions.
- [ ] **Step 4: Re-run focused tests** and expect all Task 3 tests to pass.
- [ ] **Step 5: Commit** with `feat(r6): persist and audit Track B experiments`.

### Task 4: Canonical training, documentation, and final verification

**Files:**
- Generate: `artifacts/models/track_b/r6-track-b-v1/*`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/architecture.md`
- Modify: `docs/model_training.md`
- Modify: `docs/model_evaluation.md`
- Modify: `docs/model_integration.md`
- Modify: `docs/limitations.md`
- Modify: `docs/testing.md`
- Modify: `docs/implementation_log.md`

**Interfaces:**
- Consumes: Task 3 CLI and frozen R5 local artifacts.
- Produces: one versioned Track B bundle, final audit, and R6 documentation.

- [ ] **Step 1: Run the canonical CLI once** with experiment ID `r6-track-b-v1`; inspect counts, feature order, leaderboard, selected configuration, A/B metrics, deltas, reload evidence, and 25 audit checks.
- [ ] **Step 2: Add documentation using only generated evidence.** State validation-only selection and research limitations; make no biological or causal claim.
- [ ] **Step 3: Run focused R6 tests, then full `python -m pytest`, compileall, pip check, `git diff --check`, and `git status --short`.** Expect zero failures.
- [ ] **Step 4: Self-review the complete R6 diff because no native subagent/spawn tool is exposed.** Verify no R5 file changed, no source data or engineer pickle is staged, and all report/metric values agree.
- [ ] **Step 5: Commit** with `feat(r6): train clinical genomic Cox survival model` and stop before R7/R8.
