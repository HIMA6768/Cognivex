# R7 Track C Molecular Subtype Classification Design

## Purpose

R7 adds one framework-independent molecular-subtype classification workflow to the frozen Cognivex R2–R6 foundation. It trains exactly four approved classifier families on the current canonical METABRIC training split, chooses one winner using validation Macro-F1 only, evaluates that frozen winner once on test, persists a reproducible artifact bundle, and runs a separate 28-check audit.

R7 is classification-only. It adds no Cox model, survival target, hazard metric, clinical predictor, feature-importance analysis, patient-facing result, or Streamlit model integration.

## Immutable authorities

- Prepared data: `data/metabric/prepared/METABRIC_prepared.csv` (1,904 rows, 693 columns).
- Locked manifest: `data/metabric/metadata/manifest.csv` (1,332 train, 286 validation, 286 test).
- Explicit genomic selection: `ai_handoff_data/v1/selected_features.txt`.
- Target: `pam50_+_claudin-low_subtype`.
- Existing R4D mutation parser: `src.preprocessing.mutations.classify_mutation_annotation` through the established selected-mutation transformer.
- R5 and R6 source and artifacts are frozen.

The engineer 1,332/191/381 split, engineer data loaders, dynamic genomic discovery, survival logic, historical pickles, and test-based comparisons are prohibited.

## Resolved design approach

### Selected approach: one complete sklearn pipeline per candidate

Each candidate owns a fresh preprocessing object and estimator in one sklearn `Pipeline`. This keeps train-fitted expression scaling physically attached to scale-sensitive estimators, keeps tree candidates free of unnecessary scaling, applies the same stateless mutation transformation on every split, and makes the selected winner self-contained for trusted local reload.

The alternatives are rejected:

1. A single globally transformed matrix would either scale tree inputs unnecessarily or require preprocessing state to be managed separately from model selection and persistence.
2. Forking the engineer scripts would retain incompatible split loading, dynamic feature discovery, survival code, and test evaluation of every candidate.
3. A large per-family hyperparameter search is unnecessary for this increment and would turn one validation split into a broader tuning surface.

## Feature and target contracts

### Predictors

Track C consumes exactly 68 ordered raw predictors:

- 50 expression features in selected-file order.
- 18 mutation annotation features in selected-file order.
- 0 clinical predictors.

The public transformed order is the same 50 expression names followed by 18 `<raw_mutation_name>_present` names. No predictor is discovered from dtype, prefix scans, or unused dataset columns.

### Mutation representation

The existing R4D semantics are reused rather than reimplemented:

- trimmed or numeric zero means absent and becomes `0`;
- any valid non-zero mutation annotation accepted by `classify_mutation_annotation` means present and becomes `1`;
- missing, blank, boolean, non-finite numeric, or malformed input fails clearly according to the existing R4D contract.

Implementation must reuse `src.preprocessing.mutations.classify_mutation_annotation` through the established selected-mutation transformation abstraction. It must not create a new mutation parser.

The canonical prepared CSV is read-only. The transformed mutation block must contain only `{0, 1}` for train, validation, and test.

### Target and class order

The model target is the prepared source column `pam50_+_claudin-low_subtype`. R7 persists this exact model class order:

1. `Basal`
2. `Her2`
3. `LumA`
4. `LumB`
5. `Normal`
6. `claudin-low`

`NC`, missing targets, and unsupported target values are ineligible for Track C. This exclusion does not mutate the canonical dataset and does not affect Track A, B, or D eligibility. The current canonical evidence is expected to be 1,330 eligible train rows, 285 validation rows, and 283 test rows, with NC exclusions of 2, 1, and 3 respectively; implementation must derive and verify these values rather than use them as selector constants.

The source labels are retained as model labels because the R7 contract explicitly freezes them. Display-name mappings in `subtype_labels.json` remain available to UI code but do not change estimator class identities.

### Deterministic cohort ordering

Every eligible split is resolved into canonical manifest order before prediction generation, probability generation, cohort fingerprint generation, prediction digest generation, or probability digest generation. The manifest is the existing Cognivex patient-order authority and no second ordering rule is introduced. Therefore, the same eligible cohort supplied in a different incidental DataFrame order must resolve to the same ordered rows and produce identical fingerprints and digests.

## Preprocessing

All candidates receive only the ordered 68-field DataFrame guarded by an exact-column transformer.

- Logistic Regression and RBF SVM: train-fitted `StandardScaler` on the 50 expression columns; mutation indicators remain unscaled.
- Random Forest and Gradient Boosting: expression values pass through unchanged; mutation indicators remain unscaled.
- Mutation conversion has no fitted statistics.
- Validation and test call `transform`/`predict` only. No validation/test fit or `fit_transform` is permitted.

The final persisted `pipeline.pkl` contains every transform required for inference. It is a trusted local artifact, is Git-ignored, and must never be loaded from an untrusted source.

## Candidate definitions

R7 evaluates exactly one deterministic configuration from each approved family, in this declaration order:

1. Logistic Regression: `C=1.0`, `class_weight="balanced"`, `max_iter=2000`, `random_state=42`.
2. Random Forest: `n_estimators=200`, `max_depth=8`, `class_weight="balanced"`, `n_jobs=-1`, `random_state=42`.
3. Gradient Boosting: `n_estimators=150`, `max_depth=4`, `learning_rate=0.1`, `random_state=42`.
4. RBF SVM: `C=1.0`, `kernel="rbf"`, `probability=True`, `class_weight="balanced"`, `random_state=42`.

No additional family or configuration is introduced during R7. Fixed seeds are persisted.

## Selection and test discipline

For each candidate:

1. fit its complete pipeline on eligible training rows only;
2. predict eligible validation rows;
3. compute validation Macro-F1, weighted F1, accuracy, balanced accuracy, and fixed-order per-class precision/recall/F1/support.

The winner is the candidate with the highest validation Macro-F1. Scores within an absolute tolerance of `1e-12` use declaration order as the deterministic tie-break. Test data is not accepted by the selection function.

After selection, the winner is frozen. Only that pipeline receives one final test prediction/evaluation. Candidate test-evaluation count must remain zero and frozen-winner test-evaluation count must equal one.

## Evaluation contracts

Classification metrics are framework-independent serializable dataclasses. Every split result includes:

- Macro-F1;
- weighted F1;
- accuracy;
- balanced accuracy;
- fixed-order per-class precision, recall, F1, and support;
- aggregate cohort count and fingerprint.

The final test result additionally includes a fixed-order 6×6 confusion matrix and sklearn-compatible classification report. Its confusion-matrix sum must equal the eligible test count.

All four approved estimators expose `predict_proba`. R7 records estimator class order, reorders probability columns to the frozen R7 class order, verifies each row sums approximately to one, and persists an aggregate probability-output digest rather than row-level probabilities.

## Component boundaries

- `src/contracts/track_c.py`: feature, candidate, metrics, experiment, and audit-independent value contracts.
- `src/preprocessing/track_c.py`: explicit 68-field contract loading and candidate-specific genomic preprocessing.
- `src/evaluation/classification.py`: fixed-order metric, confusion-matrix, report, and probability validation helpers.
- `src/modeling/track_c.py`: four deterministic estimator factories and complete candidate pipelines.
- `src/training/track_c.py`: canonical cohort preparation, validation-only selection, and one-time final test evaluation.
- `src/artifacts/track_c.py`: non-overwriting bundle persistence and trusted reload verification.
- `src/audit/track_c.py`: independent 28-check persisted-bundle audit.
- `scripts/train_track_c.py` and `scripts/audit_track_c.py`: direct repository-root CLIs.

These modules remain independent of Streamlit and do not import engineer training entrypoints.

## Artifact bundle

The canonical bundle is `artifacts/models/track_c/r7-track-c-v1/` and contains:

- trusted local, Git-ignored `pipeline.pkl`;
- `validation_leaderboard.csv`;
- `metrics.json`;
- `metadata.json`;
- `feature_contract.json`;
- `confusion_matrix.csv`;
- `classification_report.json`;
- `report.md`;
- `audit.json` after the separate audit;
- `checksums.sha256` covering every bundle file except itself.

No patient identifier, row-level prediction, or row-level probability is persisted. Metadata records canonical hashes, source and eligible split counts, exclusion counts, target/class order, exact features, mutation policy, candidate definitions, selected model, metrics, package versions, seeds, Git commit, and generation timestamp.

## Reload verification

Trusted reload must verify:

- pipeline class and selected family;
- transformed feature order;
- estimator and persisted class order;
- exact test prediction digest;
- exact ordered probability digest;
- probability normalization;
- recomputed test metrics and confusion matrix.

Historical engineer pickle files are never loaded.

## Audit design

The separate R7 audit emits exactly 28 numbered PASS/FAIL checks matching the user-approved checklist. It reads the persisted bundle and canonical source artifacts, reloads only the new trusted local pipeline, verifies R5 and R6 frozen source/artifact checksums, and takes the final full-suite result as explicit check-28 evidence. Any failed check makes audit status `BLOCKED`.

## Testing strategy

Tests follow red-green TDD and use controlled synthetic fixtures where model-selection behavior must be isolated. Canonical integration tests verify derived counts and immutable hashes. Coverage includes:

- exact 50/18/68 allowlist and no clinical leakage;
- target, six classes, NC/missing exclusion, and Track-C-only scope;
- shared mutation parser behavior and binary outputs;
- train-only scaling, transform-only holdouts, stable order;
- exactly four deterministic candidate families;
- validation Macro-F1 selection and declaration-order ties;
- test-inaccessible candidate selection and winner-only test evaluation;
- complete metrics, 6×6 confusion matrix, probability class ordering;
- non-overwriting persistence, ignored pickle, reload reproduction;
- all 28 audit checks.

Final verification runs R7-focused pytest, full pytest, compileall, pip check, `git diff --check`, and repository-status inspection.

## Safety and interpretation boundary

R7 is internal research/educational development evidence. It is not a diagnostic system, does not establish biological or causal relationships, and does not validate clinical utility. Test performance cannot be used to revise R7. Feature importance, gene interpretation, inference services, Streamlit results, and R8 are explicitly deferred.
