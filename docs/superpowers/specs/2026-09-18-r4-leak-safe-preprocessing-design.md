# R4 Leak-Safe Preprocessing Design

## Purpose

R4 creates task-specific, sklearn-compatible preprocessing contracts for the METABRIC research prototype. It prepares future Track A clinical survival, Track B clinical-plus-mRNA survival, and Track C molecular subtype classification work without fitting any predictive model or calculating performance metrics.

The governing invariant is that every learned preprocessing statistic is fitted only on the applicable training rows. Validation and test rows are transform-only, and future cross-validation can clone and refit the complete preprocessing object inside each training fold.

## Boundary and prerequisites

R2 remains responsible for repository-relative paths, checksum verification, canonical schema validation, the immutable patient/sample mapping, and the locked manifest. R3 remains responsible for deterministic data-quality reporting. R4 proceeds only after R2 reports `DATA_READY` and R3 reports either `DATA_QUALITY_READY` or `DATA_QUALITY_READY_WITH_WARNINGS`.

R4 reads but never rewrites:

- `data/metabric/raw/METABRIC_RNA_Mutation.csv`
- `data/metabric/prepared/METABRIC_prepared.csv`
- `data/metabric/metadata/manifest.csv`
- the existing schema, feature-group, subtype, mapping, provenance, and checksum metadata

R4 does not fit Cox models, Coxnet, subtype classifiers, or other estimators. It does not compute a C-index, predictions, risk scores, feature importance, or mutation-derived features.

## Architecture

R4 uses three explicit factories rather than a universal preprocessor:

- `build_clinical_survival_preprocessor()` for Track A.
- `build_clinical_mrna_survival_preprocessor()` for Track B.
- `build_subtype_preprocessor()` for Track C.

Each factory returns a fresh, unfitted sklearn-compatible transformer. Shared code is limited to schema loading, column guards, the two original-value missing indicators, feature-name validation, and eligibility utilities. Feature inclusion, eligibility, scaling, and target handling remain explicit per task.

The implementation is split by responsibility:

- `src/contracts/preprocessing.py`: framework-independent enums and serializable metadata contracts.
- `src/preprocessing/schema.py`: immutable feature/schema/subtype metadata loading and validation.
- `src/preprocessing/eligibility.py`: patient-aligned, task-specific masks and stable exclusion reasons.
- `src/preprocessing/clinical.py`: clinical feature policies and sklearn-compatible missing-indicator support.
- `src/preprocessing/pipelines.py`: the three public factories, ordered feature selection, feature-name extraction, and leakage guards.
- `src/preprocessing/metabric.py`: R2/R3 gating and canonical aggregate verification without exposing patient-level records to Streamlit.

## Contracts

`PreprocessingTask` freezes these values:

- `clinical_survival`
- `clinical_mrna_survival`
- `subtype_classification`

`PreprocessingTrack` freezes `Track A`, `Track B`, and `Track C`.

`EligibilityReasonCode` includes stable reasons for invalid targets or task inputs, including the required `NON_POSITIVE_SURVIVAL_DURATION`. Eligibility is represented by an ordered tuple of booleans and an equally sized tuple of per-row reason tuples. The contract is aligned to the caller's row order and intentionally contains no patient IDs.

`PreprocessingMetadata` is serializable and framework-independent. It records task, track, source dataset/version, fitted split, eligible/excluded counts, aggregate exclusion counts, raw and transformed feature counts, ordered feature names, clinical and mRNA feature names, preprocessing policies, NC and zero-duration policies, mutation policy, and forbidden-feature-guard state. It never contains patient identifiers or feature values.

## Locked split and source alignment

The committed manifest is joined to the prepared dataset by `patient_id` with one-to-one validation. R4 never assigns splits by row order and never regenerates, stratifies, shuffles, balances, or edits the manifest. A task may exclude a row while preserving its canonical split membership.

## Eligibility

### Track A — clinical survival

A row is eligible when its survival duration is present, numeric, finite, and greater than zero; its event is present and belongs to canonical `{0, 1}`; and its manifest split is valid after R2 integrity succeeds. Missing `tumor_size`, missing ER-IHC, `Unknown` tumor stage, and subtype—including `NC`—do not exclude the row.

### Track B — clinical + mRNA survival

Track B applies Track A's survival rules and additionally requires all 489 expected mRNA columns to exist in canonical order and each row's mRNA values to be numeric and finite. Subtype and mutation annotations have no effect on eligibility.

### Track C — subtype classification

Track C is independent of survival validity. The source subtype label is normalized through `subtype_labels.json` as a target operation, not a predictor transform. A row is eligible when the source label maps to one of the six declared canonical classes and all 489 mRNA values satisfy the genomic contract. `NC` is excluded with reason `NC_SUBTYPE`; zero survival duration does not exclude a row.

The Track C boundary is:

```text
X = 489 ordered mRNA predictors
y = separately normalized six-class subtype target
```

Neither the raw target nor its mapping enters the feature transformer.

## Clinical transformation

The approved clinical predictors are read from `feature_groups.json` and checked against `clinical_schema.json`:

- Numeric: `age_at_diagnosis`, `tumor_size`, `lymph_nodes_examined_positive`.
- Categorical: `tumor_stage`, `er_status_measured_by_ihc`, `pr_status`, `her2_status`.

`tumor_size` receives train-fitted median imputation. ER-IHC receives train-fitted most-frequent imputation. Before imputation, a cloneable missing-indicator transformer emits the exact public names:

- `tumor_size_was_missing`
- `er_status_measured_by_ihc_was_missing`

The indicators are derived from original input nullness and are never recomputed from imputed values.

Categorical encoding uses schema-declared category order and `OneHotEncoder(handle_unknown="ignore")`. This keeps transformed feature order deterministic and prevents validation/test-only categories from becoming fitted metadata. `Unknown` remains a valid tumor-stage category. Unexpected missingness in any other approved predictor fails clearly; R4 invents no additional imputation policy.

Track A leaves numeric predictors unscaled to preserve the interpretability of the future low-dimensional Cox baseline.

## mRNA transformation

Both genomic tracks consume exactly the 489 mRNA names in the order declared by `feature_groups.json`.

Track B applies `StandardScaler` fitted only on training rows. This is an additional model-pipeline transform for future penalized Coxnet; it does not recreate raw expression data or contradict the upstream METABRIC Z-score representation.

Track C preserves the canonical expression Z-scores without another R4 scaler while the classifier family remains unresolved. If R7 selects a scale-sensitive classifier, its scaler must live inside the future classifier pipeline and fit independently within training/CV folds.

No outcome-driven filtering, gene selection, alphabetical reordering, or permanent transformed matrix is introduced.

## Mutation policy

All 173 `*_mut` columns are annotation fields and are excluded from Tracks A, B, and C. R4 does not cast, binarize, encode, filter, count, or otherwise transform them. Track D remains deferred.

## Leakage safeguards

Task feature frames are built by explicit ordered allowlists. Final transformed feature names are validated before model consumption. Construction or metadata extraction fails if a final feature name resolves to any of:

- `patient_id`
- locked split metadata
- `overall_survival_months`
- `overall_survival`
- `pam50_+_claudin-low_subtype`
- any `*_mut` field
- eligibility flags, reason codes, or internal row-selection metadata

Factories never fit. Canonical verification fits only each task's eligible locked-training frame, then calls `transform()` on eligible validation and test frames. Future CV must receive the full preprocessor-plus-model pipeline so each fold fits its own imputers, encoder state, scaler, and any later learned selector.

## Deterministic ordering

Track A output order is numeric clinical values, categorical expansions in schema order, then the two exact missingness indicators. Track B appends the 489 scaled genes in canonical feature-group order. Track C emits only the 489 genes in canonical order. Public metadata records the complete resulting order.

## Dependencies

`pandas`, `numpy`, and `scikit-learn` move into active runtime dependencies because application-owned R4 modules import them. R4 does not add `scikit-survival`, lifelines, PyTorch, TensorFlow, XGBoost, or SHAP.

## Canonical acceptance expectations

The pre-implementation read-only analysis establishes these expected checks, which implementation must independently verify:

- Track A: 1,903 eligible; the one zero-duration validation row excluded.
- Track B: 1,903 eligible; the same row excluded; 489 mRNA predictors; zero mutation predictors.
- Track C: 1,898 eligible; six `NC` rows excluded; the zero-duration row remains eligible.
- Missing indicators: 20 original `tumor_size` nulls and 30 original ER-IHC nulls.
- Forbidden predictor leakage: zero.

These are dataset facts, not model results.

## UI and documentation

R4 does not expose transformed matrices, identifiers, outcomes, or patient-level eligibility through Streamlit. The active Methodology/About material may describe the aggregate policies, but no new prediction workflow is created. Documentation records architecture, task boundaries, fitting policy, feature ordering, eligibility, mutation deferment, limitations, tests, and the R5/R6/R7 handoff.

## Verification and gate

R4 completion requires focused preprocessing tests, the full pytest suite, compile and dependency checks, a canonical preprocessing smoke run, aggregate eligibility and feature-count reporting, mutation and forbidden-feature checks, deterministic-order checks, explicit train-only state checks, Git diff/status inspection, and a Streamlit smoke test if active UI content changes.

R4 stops after preprocessing readiness. R5, R6, and R7 modeling require separate approval.
