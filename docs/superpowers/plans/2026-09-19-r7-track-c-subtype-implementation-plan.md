# R7 Track C Molecular Subtype Classification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved R7 six-class molecular subtype classifier using the frozen 68-feature genomic contract, validation-only Macro-F1 model selection, winner-only test evaluation, reproducible artifact persistence, and the independent 28-check audit.

**Architecture:** Build one complete sklearn pipeline per approved candidate. Each pipeline owns exact-column genomic preprocessing plus its classifier; validation-only orchestration selects one pipeline, a separate finalization boundary evaluates that frozen winner once on canonically ordered test rows, and versioned persistence plus an independent audit verify the resulting evidence.

**Tech Stack:** Python, pandas, NumPy, scikit-learn, pickle as currently used by Cognivex, and existing Cognivex data/preprocessing/artifact infrastructure.

**Spec:** `docs/superpowers/specs/2026-09-19-r7-track-c-subtype-design.md`

## Global Constraints

- Active data remains `data/metabric/prepared/METABRIC_prepared.csv` with 1,904 rows and 693 columns.
- Active manifest remains `data/metabric/metadata/manifest.csv` with 1,332 train, 286 validation, and 286 test patients.
- Track C raw X is exactly 50 selected expression plus 18 selected mutation annotation fields in `ai_handoff_data/v1/selected_features.txt` order; it contains zero clinical fields.
- Target is exactly `pam50_+_claudin-low_subtype`; class order is `Basal`, `Her2`, `LumA`, `LumB`, `Normal`, `claudin-low`.
- `NC`, missing targets, and unsupported targets are excluded only from Track C; canonical rows are never mutated or removed.
- Mutation conversion must reuse `src.preprocessing.mutations.classify_mutation_annotation` through the established selected-mutation abstraction. No second parser is permitted.
- Every eligible split resolves into canonical manifest order before fingerprints, predictions, probabilities, or digests.
- Candidate families and parameters are frozen to the four definitions in Task 4.
- Validation Macro-F1 is the only selector; ties within `1e-12` use declaration order.
- Candidate selection receives no test object. Only the frozen validation winner receives one test evaluation.
- R5 and R6 source, artifacts, data hashes, and behavior remain frozen.
- Historical engineer pickles are untrusted reference material and must never be loaded.
- No Cox logic, survival evaluation, feature selection, Streamlit integration, patient inference, biological interpretation, deployment, or R8 work.

## Review Focus

- A shuffled prepared DataFrame must still resolve to canonical manifest order and identical cohort/prediction/probability digests; Task 1 and Task 7 pin this.
- Mutation strings such as `E883K` must map to present while booleans/non-finite/malformed values fail through the shared R4D parser; Task 2 pins this.
- Estimator probability columns may be alphabetically ordered rather than in the frozen class order; Task 3 and Task 6 pin explicit reordering.
- Candidate Macro-F1 scores separated by no more than `1e-12` must choose declaration order without test access; Task 5 pins this.
- A synthetic holdout missing one modeled class must still emit six ordered per-class rows and a 6×6 confusion matrix with zero support for that class; Task 3 pins this.

---

### Task 1: Track C feature, target, eligibility, and ordering contracts

**Files:**
- Create: `src/contracts/track_c.py`
- Create: `src/data/track_c.py`
- Modify: `src/contracts/__init__.py`
- Modify: `src/data/__init__.py`
- Test: `tests/test_track_c_contracts.py`

**Interfaces:**
- Consumes: canonical prepared/manifest DataFrames, `parse_selected_features(path)`, and existing `EligibilityReasonCode` meanings.
- Produces: `TRACK_C_TARGET_COLUMN`, `TRACK_C_CLASS_ORDER`, `TRACK_C_EXCLUDED_LABELS`, `TrackCFeatureContract`, `TrackCExclusionSummary`, `OrderedTrackCSplit`, `TrackCOrderedCohorts`, `load_track_c_feature_contract(repository_root, selected_features_path=None)`, `load_ordered_track_c_cohorts(prepared, manifest)`, and `ordered_patient_fingerprint(patient_ids)`.

- [ ] **Step 1: Write failing contract and canonical-order tests**

Create tests named:

```python
def test_track_c_contract_is_exactly_50_expression_18_mutation_and_no_clinical(): ...
def test_track_c_target_and_six_class_order_are_frozen(): ...
def test_track_c_excludes_nc_missing_and_unsupported_without_mutating_input(): ...
def test_nc_exclusion_does_not_change_survival_eligibility(): ...
def test_shuffled_prepared_rows_resolve_to_identical_manifest_order_and_fingerprint(): ...
def test_canonical_track_c_counts_are_1330_285_283_with_nc_2_1_3(): ...
```

Assert `contract.raw_features == expression_features + mutation_features`, all R5 clinical names are absent, the canonical target is unchanged, manifest order is retained by a left join on unique `patient_id`, and canonical counts are derived rather than stored as filtering constants.

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_track_c_contracts.py -q`

Expected: collection fails because `src.contracts.track_c` and `src.data.track_c` do not exist.

- [ ] **Step 3: Implement the smallest ordered-cohort boundary**

Implement these exact constants and signatures:

```python
TRACK_C_TARGET_COLUMN = "pam50_+_claudin-low_subtype"
TRACK_C_CLASS_ORDER = ("Basal", "Her2", "LumA", "LumB", "Normal", "claudin-low")
TRACK_C_EXCLUDED_LABELS = ("NC",)

def load_track_c_feature_contract(
    repository_root: Path,
    *,
    selected_features_path: Path | None = None,
) -> TrackCFeatureContract: ...

def load_ordered_track_c_cohorts(
    prepared: pd.DataFrame,
    manifest: pd.DataFrame,
) -> TrackCOrderedCohorts: ...

def ordered_patient_fingerprint(patient_ids: tuple[str, ...]) -> str: ...
```

`load_ordered_track_c_cohorts` must validate unique/non-null patient IDs, join each manifest split to prepared rows with `sort=False` and one-to-one validation, categorize exclusions as NC/missing/unsupported, and return eligible frames in manifest sequence. Do not normalize source class labels or persist patient IDs.

- [ ] **Step 4: Run focused and relevant eligibility tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_track_c_contracts.py tests\test_preprocessing_eligibility.py -q`

Expected: all tests pass; canonical counts are train 1,330, validation 285, test 283.

- [ ] **Step 5: Commit Task 1**

```powershell
git add src/contracts/track_c.py src/data/track_c.py src/contracts/__init__.py src/data/__init__.py tests/test_track_c_contracts.py
git commit -m "feat(r7): add Track C feature and cohort contracts"
```

---

### Task 2: Candidate-specific Track C preprocessing

**Files:**
- Create: `src/preprocessing/track_c.py`
- Modify: `src/preprocessing/__init__.py`
- Test: `tests/test_track_c_preprocessing.py`

**Interfaces:**
- Consumes: `TrackCFeatureContract`, `FeatureFrameGuard`, and existing `SelectedMutationPresenceTransformer`, which delegates to `classify_mutation_annotation`.
- Produces: `build_track_c_preprocessor(contract, *, scale_expression) -> Pipeline` and `track_c_feature_names(preprocessor) -> tuple[str, ...]`.

- [ ] **Step 1: Write failing preprocessing tests**

Create tests named:

```python
def test_track_c_preprocessor_guards_exact_68_column_order(): ...
def test_lr_and_svm_expression_blocks_fit_training_standard_scaler_only(): ...
def test_rf_and_gb_expression_blocks_remain_unscaled(): ...
def test_mutation_transformer_is_existing_selected_r4d_abstraction(): ...
def test_zero_and_e883k_map_to_binary_and_bool_or_malformed_fail(): ...
def test_mutation_block_is_unscaled_binary_and_source_frame_is_unchanged(): ...
def test_transformed_names_are_50_expression_then_18_present_indicators(): ...
```

Use controlled train and holdout frames with deliberately different expression means. Assert training-scaled expression means are approximately zero, holdout values reflect training statistics, tree expression values remain byte-equivalent, and all transformed mutation values are `{0, 1}`.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_track_c_preprocessing.py -q`

Expected: collection fails because `src.preprocessing.track_c` does not exist.

- [ ] **Step 3: Implement the exact composite transformer**

Implement:

```python
def build_track_c_preprocessor(
    contract: TrackCFeatureContract,
    *,
    scale_expression: bool,
) -> Pipeline: ...

def track_c_feature_names(preprocessor: Pipeline) -> tuple[str, ...]: ...
```

The pipeline must guard `contract.raw_features`, apply `StandardScaler()` or `"passthrough"` to the ordered expression columns, and apply the imported `SelectedMutationPresenceTransformer(contract.mutation_features)` to mutation columns. `track_c_feature_names` must require exactly 68 unique safe names in the frozen order.

- [ ] **Step 4: Run focused and shared mutation tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_track_c_preprocessing.py tests\test_track_b_preprocessing.py tests\test_mutation_preprocessing.py -q`

Expected: all tests pass; no new parser exists and R6 behavior remains green.

- [ ] **Step 5: Commit Task 2**

```powershell
git add src/preprocessing/track_c.py src/preprocessing/__init__.py tests/test_track_c_preprocessing.py
git commit -m "feat(r7): add leak-safe Track C preprocessing"
```

---

### Task 3: Fixed-order classification evaluation utilities

**Files:**
- Create: `src/evaluation/classification.py`
- Modify: `src/evaluation/__init__.py`
- Modify: `src/contracts/track_c.py`
- Modify: `src/contracts/__init__.py`
- Test: `tests/test_classification_evaluation.py`

**Interfaces:**
- Consumes: frozen class order and canonically ordered patient IDs from Task 1.
- Produces: `PerClassClassificationMetric`, `ClassificationMetrics`, `ProbabilityOutput`, `evaluate_classification(y_true, y_pred, *, split, class_order, cohort_fingerprint)`, `reorder_and_validate_probabilities(probabilities, estimator_classes, class_order)`, `prediction_digest(predictions)`, and `probability_digest(ordered_probabilities)`.

- [ ] **Step 1: Write failing metric and probability tests**

Create tests named:

```python
def test_classification_metrics_match_sklearn_macro_weighted_accuracy_and_balanced_accuracy(): ...
def test_per_class_metrics_and_confusion_matrix_always_use_six_class_order(): ...
def test_missing_holdout_class_keeps_zero_support_and_six_by_six_matrix(): ...
def test_confusion_matrix_sum_equals_evaluated_row_count(): ...
def test_probability_columns_reorder_from_estimator_order_to_frozen_order(): ...
def test_probability_rows_must_sum_to_one_and_reject_missing_or_duplicate_classes(): ...
def test_ordered_prediction_probability_and_cohort_digests_are_stable(): ...
```

Recompute Macro-F1 directly with `sklearn.metrics.f1_score(..., labels=TRACK_C_CLASS_ORDER, average="macro", zero_division=0)` and compare exactly within floating-point tolerance.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_classification_evaluation.py -q`

Expected: collection fails because classification contracts/utilities do not exist.

- [ ] **Step 3: Implement fixed-order metrics and canonical byte digests**

Implement:

```python
def evaluate_classification(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    *,
    split: str,
    class_order: tuple[str, ...],
    cohort_fingerprint: str,
) -> ClassificationMetrics: ...

def reorder_and_validate_probabilities(
    probabilities: np.ndarray,
    estimator_classes: Sequence[str],
    class_order: tuple[str, ...],
) -> ProbabilityOutput: ...
```

Use explicit `labels=class_order` for every sklearn metric/report call. Digest UTF-8 newline-joined ordered predictions and canonical little-endian float64 ordered probabilities. Reject non-finite probabilities, class-set mismatch, and row sums outside `np.allclose(..., 1.0, atol=1e-8, rtol=0)`.

- [ ] **Step 4: Run focused evaluation tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_classification_evaluation.py -q`

Expected: all tests pass, including the missing-class and estimator-order cases.

- [ ] **Step 5: Run contract regressions and commit**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_contracts.py tests\test_track_c_contracts.py tests\test_classification_evaluation.py -q`

Expected: all tests pass.

```powershell
git add src/evaluation/classification.py src/evaluation/__init__.py src/contracts/track_c.py src/contracts/__init__.py tests/test_classification_evaluation.py
git commit -m "feat(r7): add fixed-order classification evaluation"
```

---

### Task 4: Four frozen candidate model factories

**Files:**
- Create: `src/modeling/track_c.py`
- Modify: `src/modeling/__init__.py`
- Modify: `src/contracts/track_c.py`
- Modify: `src/contracts/__init__.py`
- Test: `tests/test_track_c_models.py`

**Interfaces:**
- Consumes: Task 2 `build_track_c_preprocessor` and `TrackCFeatureContract`.
- Produces: `TrackCCandidateDefinition`, `TRACK_C_CANDIDATES`, and `build_track_c_candidate(definition, contract) -> Pipeline`.

- [ ] **Step 1: Write failing exact-factory tests**

Create tests named:

```python
def test_candidate_registry_contains_exactly_four_families_in_frozen_order(): ...
def test_logistic_configuration_and_scaling_are_exact(): ...
def test_random_forest_configuration_and_unscaled_expression_are_exact(): ...
def test_gradient_boosting_configuration_and_unscaled_expression_are_exact(): ...
def test_rbf_svm_configuration_probability_and_scaling_are_exact(): ...
def test_all_supported_random_states_are_42_and_factory_is_deterministic(): ...
def test_track_c_model_module_has_no_lifelines_or_survival_import(): ...
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_track_c_models.py -q`

Expected: collection fails because `src.modeling.track_c` does not exist.

- [ ] **Step 3: Implement exact definitions and pipeline factory**

Define the registry in this order and with these parameters:

```python
TRACK_C_CANDIDATES = (
    TrackCCandidateDefinition("logistic_regression", "Logistic Regression", True, {"C": 1.0, "class_weight": "balanced", "max_iter": 2000, "random_state": 42}),
    TrackCCandidateDefinition("random_forest", "Random Forest", False, {"n_estimators": 200, "max_depth": 8, "class_weight": "balanced", "n_jobs": -1, "random_state": 42}),
    TrackCCandidateDefinition("gradient_boosting", "Gradient Boosting", False, {"n_estimators": 150, "max_depth": 4, "learning_rate": 0.1, "random_state": 42}),
    TrackCCandidateDefinition("rbf_svm", "RBF SVM", True, {"C": 1.0, "kernel": "rbf", "probability": True, "class_weight": "balanced", "random_state": 42}),
)
```

`build_track_c_candidate` returns `Pipeline([("preprocessor", ...), ("classifier", estimator)])` and rejects unregistered family keys.

- [ ] **Step 4: Run focused and preprocessing tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_track_c_models.py tests\test_track_c_preprocessing.py -q`

Expected: all tests pass and the registry contains no fifth candidate.

- [ ] **Step 5: Commit Task 4**

```powershell
git add src/modeling/track_c.py src/modeling/__init__.py src/contracts/track_c.py src/contracts/__init__.py tests/test_track_c_models.py
git commit -m "feat(r7): add frozen subtype candidate factories"
```

---

### Task 5: Validation-only training and model selection

**Files:**
- Create: `src/training/track_c.py`
- Modify: `src/training/__init__.py`
- Modify: `src/contracts/track_c.py`
- Modify: `src/contracts/__init__.py`
- Test: `tests/test_track_c_selection.py`

**Interfaces:**
- Consumes: Tasks 1–4 contracts, ordered cohorts, metrics, and candidate pipelines.
- Produces: `PreparedTrackCSelection`, `PreparedTrackCTest`, `PreparedTrackCRun`, `TrackCCandidateResult`, `SelectedTrackCModel`, `prepare_track_c_run(paths=None) -> PreparedTrackCRun`, and `select_track_c_candidate(selection, *, candidates=TRACK_C_CANDIDATES, pipeline_factory=build_track_c_candidate) -> SelectedTrackCModel`.

- [ ] **Step 1: Write failing preparation and selection tests**

Create tests named:

```python
def test_prepare_track_c_run_uses_current_dataset_manifest_and_exact_eligible_counts(): ...
def test_prepared_selection_contains_train_validation_but_no_test_fields(): ...
def test_candidate_fit_receives_train_rows_and_validation_only_receives_predict(): ...
def test_highest_validation_macro_f1_is_sole_winner_even_if_fake_test_scores_disagree(): ...
def test_macro_f1_ties_within_one_e_minus_12_choose_declaration_order(): ...
def test_selection_is_reproducible_with_fixed_seed_candidates(): ...
def test_shuffled_prepared_source_produces_identical_selection_cohort_fingerprints(): ...
```

Use instrumented fake pipelines for selector-discipline tests. Their API must expose `fit`, `predict`, `predict_proba`, `classes_`, and counters so the test proves selection never receives a `PreparedTrackCTest` object.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_track_c_selection.py -q`

Expected: collection fails because `src.training.track_c` and selection-result contracts do not exist.

- [ ] **Step 3: Implement canonical preparation and validation-only selection**

Implement:

```python
def prepare_track_c_run(paths: MetabricPaths | None = None) -> PreparedTrackCRun: ...

def select_track_c_candidate(
    selection: PreparedTrackCSelection,
    *,
    candidates: tuple[TrackCCandidateDefinition, ...] = TRACK_C_CANDIDATES,
    pipeline_factory: Callable = build_track_c_candidate,
) -> SelectedTrackCModel: ...
```

`prepare_track_c_run` must verify R2 `DATA_READY` and non-blocked R3 quality, load current hashes, resolve manifest order through Task 1, construct exact 68-column copies indexed by unique patient ID, and store each split's canonical manifest-ordered patient-ID tuple separately. Test remains in the distinct `PreparedTrackCTest` field. `select_track_c_candidate` must fit four fresh pipelines on train, compute validation metrics, store complete per-class validation metrics, and compare only Macro-F1 with `math.isclose(abs_tol=1e-12, rel_tol=0)` plus declaration order.

- [ ] **Step 4: Run focused selection tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_track_c_selection.py -q`

Expected: all tests pass; candidate test-evaluation count is zero.

- [ ] **Step 5: Run R2–R7 data/preprocessing regressions and commit**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_metabric_ingestion.py tests\test_preprocessing_eligibility.py tests\test_track_b_training.py tests\test_track_c_contracts.py tests\test_track_c_selection.py -q`

Expected: all tests pass and canonical data hashes remain unchanged.

```powershell
git add src/training/track_c.py src/training/__init__.py src/contracts/track_c.py src/contracts/__init__.py tests/test_track_c_selection.py
git commit -m "feat(r7): add validation-only subtype selection"
```

---

### Task 6: Frozen-winner final test evaluation

**Files:**
- Modify: `src/training/track_c.py`
- Modify: `src/contracts/track_c.py`
- Modify: `src/contracts/__init__.py`
- Test: `tests/test_track_c_finalization.py`

**Interfaces:**
- Consumes: `SelectedTrackCModel`, `PreparedTrackCTest`, Task 3 metrics/probability helpers.
- Produces: `TrackCExperimentResult` and `finalize_track_c(selection, test, *, experiment_id) -> TrackCExperimentResult`.

- [ ] **Step 1: Write failing winner-only finalization tests**

Create tests named:

```python
def test_finalize_calls_test_predict_and_predict_proba_exactly_once_on_winner(): ...
def test_alternative_candidates_never_receive_test_evaluation(): ...
def test_final_metrics_confusion_and_classification_report_recompute(): ...
def test_final_confusion_matrix_is_six_by_six_and_sums_to_test_count(): ...
def test_probability_rows_reorder_to_frozen_class_order_and_sum_to_one(): ...
def test_prediction_probability_and_cohort_digests_use_canonical_test_order(): ...
def test_different_incidental_test_frame_order_produces_identical_final_digests(): ...
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_track_c_finalization.py -q`

Expected: import or attribute failure because finalization contracts/functions do not exist.

- [ ] **Step 3: Implement one-time finalization**

Implement:

```python
def finalize_track_c(
    selection: SelectedTrackCModel,
    test: PreparedTrackCTest,
    *,
    experiment_id: str,
) -> TrackCExperimentResult: ...
```

The function validates canonical test order, calls only the selected pipeline, computes fixed-order metrics/report/confusion/probabilities, stores digests, and sets `candidate_test_evaluation_count=0` and `winner_test_evaluation_count=1`. It must reject blank/path-unsafe experiment identifiers and a test cohort fingerprint inconsistent with its ordered patient IDs.

- [ ] **Step 4: Run finalization and selection tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_track_c_finalization.py tests\test_track_c_selection.py tests\test_classification_evaluation.py -q`

Expected: all tests pass and no candidate-wide test result exists.

- [ ] **Step 5: Commit Task 6**

```powershell
git add src/training/track_c.py src/contracts/track_c.py src/contracts/__init__.py tests/test_track_c_finalization.py
git commit -m "feat(r7): add winner-only subtype test evaluation"
```

---

### Task 7: Artifact persistence and trusted reload verification

**Files:**
- Create: `src/artifacts/track_c.py`
- Modify: `src/artifacts/__init__.py`
- Modify: `.gitignore`
- Test: `tests/test_track_c_artifacts.py`

**Interfaces:**
- Consumes: `SelectedTrackCModel`, `TrackCExperimentResult`, `PreparedTrackCTest`, and trusted-local pickle loader.
- Produces: `TrackCReloadVerification`, `write_track_c_artifacts(selection, result, run, output_root) -> Path`, `verify_track_c_reload(bundle, test) -> TrackCReloadVerification`, `verify_track_c_checksums(bundle) -> bool`, and `refresh_track_c_checksums(bundle)`.

- [ ] **Step 1: Write failing bundle and reload tests**

Create tests named:

```python
def test_track_c_bundle_contains_required_aggregate_files_and_ignored_pipeline(): ...
def test_track_c_bundle_refuses_to_overwrite_existing_experiment(): ...
def test_metadata_contains_dataset_counts_exclusions_features_candidates_metrics_and_seeds(): ...
def test_reload_reproduces_predictions_ordered_probabilities_metrics_and_confusion(): ...
def test_reload_retains_frozen_feature_and_class_orders(): ...
def test_checksums_cover_every_bundle_file_except_checksums_itself(): ...
def test_shuffled_input_is_canonically_reordered_before_reload_digests(): ...
def test_bundle_contains_no_patient_ids_or_row_level_outputs(): ...
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_track_c_artifacts.py -q`

Expected: collection fails because `src.artifacts.track_c` does not exist.

- [ ] **Step 3: Implement non-overwriting persistence and exact reload**

Write these bundle files: `pipeline.pkl`, `validation_leaderboard.csv`, `metrics.json`, `metadata.json`, `feature_contract.json`, `confusion_matrix.csv`, `classification_report.json`, `report.md`, and `checksums.sha256`. Add `artifacts/models/**/pipeline.pkl` to `.gitignore`.

`verify_track_c_reload` must load only with `trusted=True`, restore canonical test order, reproduce predictions/probabilities, compare prediction and probability digests, recompute test metrics/confusion, and compare feature/class order. `checksums.sha256` must include the local pipeline hash even though the binary is ignored.

- [ ] **Step 4: Run artifact and finalization tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_track_c_artifacts.py tests\test_track_c_finalization.py -q`

Expected: all tests pass and the trusted pipeline is ignored at a repository artifact path.

- [ ] **Step 5: Commit Task 7**

```powershell
git add .gitignore src/artifacts/track_c.py src/artifacts/__init__.py tests/test_track_c_artifacts.py
git commit -m "feat(r7): persist and reload subtype artifacts"
```

---

### Task 8: Training CLI and deterministic R7 report

**Files:**
- Create: `scripts/train_track_c.py`
- Modify: `src/artifacts/track_c.py`
- Test: `tests/test_track_c_cli.py`
- Test: `tests/test_track_c_report.py`

**Interfaces:**
- Consumes: `prepare_track_c_run`, `select_track_c_candidate`, `finalize_track_c`, and `write_track_c_artifacts`.
- Produces: direct CLI arguments `--experiment-id` and `--output-root`, plus `render_track_c_report(result, metadata) -> str`.

- [ ] **Step 1: Write failing CLI and report tests**

Create tests named:

```python
def test_track_c_training_cli_help_runs_from_repository_root(): ...
def test_track_c_training_cli_rejects_path_unsafe_experiment_id(): ...
def test_report_contains_objective_counts_target_classes_nc_policy_features_and_candidates(): ...
def test_report_contains_validation_leaderboard_selected_reason_test_metrics_per_class_and_confusion(): ...
def test_report_states_test_not_used_for_selection_and_avoids_biological_claims(): ...
def test_report_is_deterministic_for_same_experiment_result(): ...
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_track_c_cli.py tests\test_track_c_report.py -q`

Expected: direct CLI test fails because `scripts/train_track_c.py` does not exist and report renderer is absent.

- [ ] **Step 3: Implement the direct CLI and report renderer**

The CLI must insert repository root into `sys.path`, accept only lowercase path-safe experiment IDs matching `[a-z0-9][a-z0-9._-]*`, default output to `artifacts/models/track_c`, and execute preparation → validation selection → final test → persistence once. `render_track_c_report` must render persisted aggregate values only and include the exact statement: `The test set was not used for model selection.`

- [ ] **Step 4: Run CLI/report and artifact tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_track_c_cli.py tests\test_track_c_report.py tests\test_track_c_artifacts.py -q`

Expected: all tests pass; no model training occurs in the `--help` subprocess.

- [ ] **Step 5: Commit Task 8**

```powershell
git add scripts/train_track_c.py src/artifacts/track_c.py tests/test_track_c_cli.py tests/test_track_c_report.py
git commit -m "feat(r7): add subtype training CLI and report"
```

---

### Task 9: Independent 28-check R7 audit

**Files:**
- Create: `src/audit/track_c.py`
- Create: `scripts/audit_track_c.py`
- Modify: `src/audit/__init__.py`
- Test: `tests/test_track_c_audit.py`

**Interfaces:**
- Consumes: persisted Track C bundle, canonical data/manifest, R5/R6 frozen artifacts, `verify_track_c_reload`, and externally supplied full-suite evidence.
- Produces: `TrackCAuditCheck`, `TrackCAuditReport`, `audit_persisted_track_c(bundle, *, repository_root, full_test_suite_passed, full_test_suite_summary)`, and `write_track_c_audit(bundle, audit)`.

- [ ] **Step 1: Write failing audit tests**

Create tests named:

```python
def test_r7_audit_contains_exactly_numbered_28_checks_and_all_pass_for_valid_bundle(): ...
def test_any_failed_audit_check_makes_status_blocked(): ...
def test_check_28_fails_without_full_suite_evidence(): ...
def test_audit_verifies_r5_and_r6_source_and_bundle_checksums(): ...
def test_audit_cli_help_runs_from_repository_root(): ...
def test_audit_cli_reads_literal_pytest_summary_from_evidence_file(): ...
```

Assert exact check numbers/names for: dataset, split, R5, R6, 68 total, 50 expression, 18 mutation, no clinical, target, Track-C-only NC, six classes, R4D semantics, source immutability, binary mutations, train-only preprocessing, transform-only holdouts, four families, validation Macro-F1 selection, no test influence, winner-only test, no engineer pickles, reload, prediction reproduction, class order, feature order, confusion sum, report/metrics agreement, and full-suite status.

- [ ] **Step 2: Run the focused audit test and verify RED**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_track_c_audit.py -q`

Expected: collection fails because Track C audit types and CLI do not exist.

- [ ] **Step 3: Implement all 28 independent checks**

Implement the exact signature:

```python
def audit_persisted_track_c(
    bundle: Path,
    *,
    repository_root: Path,
    full_test_suite_passed: bool,
    full_test_suite_summary: str,
) -> TrackCAuditReport: ...
```

Checks 3 and 4 must compare frozen source paths against commits `93f669cf7638a09bcff0434f9f93590aa0c552e1` and `49a8414c1aa828c07cfa9f9dd207a2bdf311b078`, then verify their local bundle checksum manifests. Check 21 must inspect the persisted estimator module and reject `cognivex_ml`. Check 28 consumes only explicit final-suite evidence. The audit CLI must accept `--full-test-suite-summary-file`, read the final pytest summary line from that UTF-8 evidence file, and reject a file with no passed-summary line. Any false check yields `BLOCKED`.

- [ ] **Step 4: Run audit, artifact, and frozen-model regression tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_track_c_audit.py tests\test_track_c_artifacts.py tests\test_track_b_audit.py tests\test_track_a_training.py -q`

Expected: all tests pass and the R7 audit has exactly 28 checks.

- [ ] **Step 5: Commit Task 9**

```powershell
git add src/audit/track_c.py scripts/audit_track_c.py src/audit/__init__.py tests/test_track_c_audit.py
git commit -m "feat(r7): add independent subtype audit"
```

---

### Task 10: Canonical training, provenance regression, documentation, and final verification

**Files:**
- Generate: `artifacts/models/track_c/r7-track-c-v1/*`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/architecture.md`
- Modify: `docs/model_training.md`
- Modify: `docs/model_evaluation.md`
- Modify: `docs/model_integration.md`
- Modify: `docs/limitations.md`
- Modify: `docs/testing.md`
- Modify: `docs/implementation_log.md`
- Test: `tests/test_r7_canonical_provenance.py`

**Interfaces:**
- Consumes: completed R7 CLI, artifact writer/reloader, and audit CLI.
- Produces: one canonical `r7-track-c-v1` bundle, one 28-check audit, updated evidence-only documentation, and final R7 commits.

- [ ] **Step 1: Write the failing canonical provenance test**

Create tests named:

```python
def test_canonical_r7_nonbinary_bundle_has_expected_identity_and_all_28_audit_checks(): ...
def test_canonical_r7_metrics_report_confusion_and_classification_report_agree(): ...
def test_canonical_r7_evidence_contains_no_patient_rows_and_preserves_r5_r6_data_hashes(): ...
```

The tests must read committed JSON/CSV/Markdown only, verify experiment ID `r7-track-c-v1`, require 68 features and the frozen class order, recompute the confusion sum and winner from the validation leaderboard, and compare documented metrics to `metrics.json`. Do not require the ignored local `pipeline.pkl` for these provenance tests.

- [ ] **Step 2: Run the provenance test and verify RED**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_r7_canonical_provenance.py -q`

Expected: FAIL because `artifacts/models/track_c/r7-track-c-v1/metadata.json` does not exist before canonical training.

- [ ] **Step 3: Run all R7-focused tests before touching canonical test evaluation**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_track_c_contracts.py tests\test_track_c_preprocessing.py tests\test_classification_evaluation.py tests\test_track_c_models.py tests\test_track_c_selection.py tests\test_track_c_finalization.py tests\test_track_c_artifacts.py tests\test_track_c_cli.py tests\test_track_c_report.py tests\test_track_c_audit.py -q
```

Expected: all R7-focused tests pass. If training/selection code fails, correct it with train/validation or synthetic fixtures before proceeding; do not inspect canonical test metrics.

- [ ] **Step 4: Execute canonical R7 training exactly once**

Run: `.\.venv\Scripts\python.exe scripts\train_track_c.py --experiment-id r7-track-c-v1`

Expected: one non-overwriting bundle is created; all four candidates appear only in the validation leaderboard; one selected model has final test metrics; source dataset hashes are unchanged.

- [ ] **Step 5: Inspect generated evidence manually before documentation**

Verify `metadata.json`, `metrics.json`, `feature_contract.json`, `validation_leaderboard.csv`, `confusion_matrix.csv`, `classification_report.json`, `report.md`, and `checksums.sha256`. Recompute the validation winner, final metrics, confusion sum, class order, feature order, prediction digest, and probability digest with a read-only verification command. Confirm no patient IDs, row predictions, secrets, historical pickles, or source datasets entered the bundle.

- [ ] **Step 6: Update documentation from generated values only**

Document actual eligible counts, validation leaderboard, selected model/reason, final test metrics, artifact boundary, validation-only selection, winner-only test access, and limitations. Do not claim biological causality, clinical validity, or performance beyond the locked internal split.

- [ ] **Step 7: Run focused provenance and the complete repository verification**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_r7_canonical_provenance.py -q
$r7FullPytestOutput = & .\.venv\Scripts\python.exe -m pytest -q 2>&1
$r7FullPytestExit = $LASTEXITCODE
$r7FullPytestOutput | Tee-Object -FilePath .superpowers/sdd/r7-track-c-subtype-implementation-plan/full-pytest.txt
if ($r7FullPytestExit -ne 0) { exit $r7FullPytestExit }
.\.venv\Scripts\python.exe -m compileall -q app.py src scripts tests
.\.venv\Scripts\python.exe -m pip check
git diff --check
git status --short
```

Expected: full pytest has zero failures; compileall exits 0; pip reports `No broken requirements found.`; diff check exits 0; status contains only intended R7 files plus the pre-existing untracked `ai_handoff_data/` material and ignored local model binaries.

- [ ] **Step 8: Run and persist the final independent audit**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\audit_track_c.py --full-test-suite-passed --full-test-suite-summary-file .superpowers/sdd/r7-track-c-subtype-implementation-plan/full-pytest.txt
```

Expected: audit status `PASS`, checks 1–28 all `passed=true`, and refreshed checksums include `audit.json` plus the ignored `pipeline.pkl`.

- [ ] **Step 9: Self-review the complete R7 branch**

Compare implementation and artifacts line-by-line to the spec and this plan. Verify `git diff --name-only 49a8414 --` contains no R5/R6 source or artifact modification, `git diff --name-only -- data` is empty, engineer pickle paths were never loaded, and R8/Streamlit/inference code is absent. Record any ruling or deferred minor in the execution ledger.

- [ ] **Step 10: Commit documentation, provenance tests, and reproducible non-binary evidence**

```powershell
git add README.md CHANGELOG.md docs/architecture.md docs/model_training.md docs/model_evaluation.md docs/model_integration.md docs/limitations.md docs/testing.md docs/implementation_log.md tests/test_r7_canonical_provenance.py artifacts/models/track_c/r7-track-c-v1/audit.json artifacts/models/track_c/r7-track-c-v1/checksums.sha256 artifacts/models/track_c/r7-track-c-v1/feature_contract.json artifacts/models/track_c/r7-track-c-v1/metadata.json artifacts/models/track_c/r7-track-c-v1/metrics.json artifacts/models/track_c/r7-track-c-v1/validation_leaderboard.csv artifacts/models/track_c/r7-track-c-v1/confusion_matrix.csv artifacts/models/track_c/r7-track-c-v1/classification_report.json artifacts/models/track_c/r7-track-c-v1/report.md
git commit -m "feat(r7): train molecular subtype classifier"
```

Do not add `pipeline.pkl`; confirm `.gitignore` protects it. Stop before R8.
