# R4D Track D Mutation Preprocessing Design

## Purpose

R4D adds leak-safe preprocessing for Track D, the clinical-plus-mutation survival prognosis track. It converts the 173 canonical METABRIC mutation annotation fields into fold-local binary mutation predictors, adds a stable all-gene mutation-burden feature, composes those features with the approved clinical baseline, and exposes auditable framework-independent metadata. R4D does not fit a survival model or calculate model performance.

The central invariant is that every learned Track D statistic is fitted only on the rows passed to `fit()`. The complete preprocessor is cloneable and can later live inside a penalized-Cox cross-validation pipeline so imputation, scaling, and mutation-frequency selection are independently refitted within each fold.

## Boundary and prerequisites

R4D proceeds only after canonical R2 ingestion reports `DATA_READY` and R3 data quality is not blocked. It builds on R4 without changing Track A, Track B, or Track C behavior. R4D-P0 aggregate mutation profiling remains descriptive evidence and is not the selector implementation.

R4D reads but never rewrites:

- `data/metabric/raw/METABRIC_RNA_Mutation.csv`
- `data/metabric/prepared/METABRIC_prepared.csv`
- `data/metabric/metadata/manifest.csv`
- `data/metabric/metadata/feature_groups.json`
- `data/metabric/metadata/clinical_schema.json`
- `data/metabric/metadata/subtype_labels.json`
- the remaining canonical mapping, provenance, and checksum metadata
- the committed R4D-P0 artifacts under `results/`

R4D does not fit Cox PH, Coxnet, Cox-Lasso, Cox-Ridge, or Cox Elastic Net. It does not compute C-index, hazard ratios, predictions, risk scores, hyperparameters, outcome-associated gene rankings, SHAP values, or patient-level mutation output. It does not begin R5, R6, R7, or R8.

## Track contract

Track naming remains:

- Track A: clinical-only survival
- Track B: clinical plus mRNA survival
- Track C: molecular subtype classification
- Track D: clinical plus mutation survival prognosis

R4D adds the stable task identifier `clinical_mutation_survival`, the stable track value `Track D`, and the public factory `build_clinical_mutation_survival_preprocessor(schema)`. The factory returns a fresh, unfitted, sklearn-compatible object suitable for `sklearn.base.clone` and future fold-local fitting.

Track D accepts only the seven approved clinical source fields and all 173 mutation annotation source fields. It does not accept mRNA predictors, subtype labels, patient identifiers, split fields, survival outcomes, eligibility metadata, or other row metadata.

## Shared mutation-annotation semantics

One pure parser is shared by R4D-P0 profiling, Track D eligibility, frequency selection, and burden calculation. It classifies immutable source values as follows:

- trimmed string `"0"` or finite numeric zero: no reported mutation;
- a non-empty nonnumeric annotation string or finite nonzero numeric value: mutation reported;
- blank or null: missing mutation value;
- boolean or non-finite numeric representation: invalid mutation value.

The parser returns semantic presence rather than numeric annotation magnitude. Annotation strings are never ordinal-encoded or cast into predictor values. Raw mutation columns are never modified or written back to a canonical CSV.

Missing mutation values are not imputed because no missing-mutation semantics have been approved. Track D eligibility records `MISSING_MUTATION_VALUE`; malformed values record `INVALID_MUTATION_VALUE`. The preprocessing transformers also fail clearly if invalid rows bypass eligibility.

## Fit-local mutation-frequency selector

`MutationFrequencySelector` is an sklearn-compatible transformer initialized with the ordered canonical mutation columns and a prevalence threshold. The Track D public factory fixes the threshold at `0.05`.

During `fit()` the selector:

1. validates that its complete ordered source-column contract is present;
2. derives binary mutation presence using the shared parser;
3. computes prevalence independently for every source gene using only the fit rows;
4. retains genes where prevalence is greater than or equal to `0.05`;
5. stores fitted prevalence and selection metadata; and
6. preserves canonical source-column order in the retained output.

During `transform()` it validates and parses the source fields but emits only the genes selected during `fit()`. It never recalculates prevalence or changes the selected set from validation/test values.

Derived names use `<raw-column>_present`, for example `pik3ca_mut_present`. The current full locked training split retains 27 genes, but neither that list nor that count is a production constant. Future cross-validation folds may retain different genes, which is expected and reportable behavior.

## Mutation burden

`MutationBurdenTransformer` deterministically parses all 173 canonical mutation annotation fields, sums binary mutation presence across all 173 genes, and emits one feature:

`mutation_burden_log1p = log1p(number of genes with mutation_present == 1)`

Burden does not depend on the frequency-selected gene set. Raw burden is documented as the source calculation but is not emitted alongside the log-transformed feature. The formula itself has no learned state; its downstream scaler is train-fitted inside the Track D pipeline.

## Clinical composition and Track D scaling

Track D reuses the approved R4 clinical policies:

- `tumor_size`: original-value missing indicator and train-fitted median imputation;
- ER-IHC: original-value missing indicator, train-fitted most-frequent imputation, and schema-ordered unknown-safe one-hot encoding;
- `tumor_stage`: preserve the canonical `Unknown` category without imputation;
- `pr_status` and `her2_status`: schema-ordered unknown-safe one-hot encoding;
- exact indicators: `tumor_size_was_missing` and `er_status_measured_by_ihc_was_missing`.

Track D has a task-specific scaling layer for its future scale-sensitive penalized Cox estimator. The following final features are train-fitted standardized continuous variables:

- `age_at_diagnosis`
- imputed `tumor_size`
- `lymph_nodes_examined_positive`
- `mutation_burden_log1p`

The following final features remain unscaled:

- all schema-ordered clinical one-hot variables;
- `tumor_size_was_missing`;
- `er_status_measured_by_ihc_was_missing`;
- all retained binary `*_mut_present` variables.

Public Track D metadata explicitly records these two ordered groups as `standardized_continuous_feature_names` and `unscaled_binary_feature_names`. This declaration is checked against the final feature order so every Track D output is classified exactly once. Track A remains unscaled, Track B retains its existing mRNA-only scaling, and Track C remains unchanged.

## Pipeline architecture and output order

The Track D factory composes three branches behind an exact input-frame guard:

```text
7 clinical + 173 mutation source columns
  |
  +-- Track D clinical branch
  |     +-- train-fitted scaled continuous clinical fields
  |     +-- schema-ordered unscaled one-hot fields
  |     +-- exact unscaled original-value missing indicators
  |
  +-- MutationFrequencySelector
  |     +-- fit-selected unscaled binary *_mut_present fields
  |
  +-- all-gene mutation burden branch
        +-- log1p burden
        +-- train-fitted StandardScaler
```

Final feature order is deterministic:

1. 16 clinical transformed features in the approved R4 order;
2. retained mutation-presence features in canonical source order; and
3. `mutation_burden_log1p`.

On the current full locked training split, the observed evidence is 16 clinical features, 27 retained mutation indicators, one burden feature, and 44 total transformed features. The values 27 and 44 are canonical integration evidence only. They are never used to configure, branch, or drive production transformation behavior.

## Track D eligibility

`evaluate_clinical_mutation_survival_eligibility()` composes the existing survival contract with mutation structural validity. A row is eligible only when:

- survival duration is present, numeric, finite, and greater than zero;
- survival event is present and belongs to `{0, 1}`;
- its patient maps to exactly one valid locked manifest split;
- canonical R2 patient/sample integrity has passed at the service boundary; and
- all required mutation source fields are structurally valid under the shared parser.

Approved imputable clinical missingness does not exclude a row. `NC` subtype status has no effect. Mutation prevalence has no effect. The zero-duration row remains excluded with `NON_POSITIVE_SURVIVAL_DURATION`.

The expected canonical result is 1,332 train, 285 validation, and 286 test rows, for 1,903 eligible rows, but these values are calculated from canonical inputs and never hardcoded in eligibility logic.

## Framework-independent metadata

The existing preprocessing contracts are extended with Track D and typed mutation metadata. Fitted metadata records:

- task, track, source dataset/version, fit split, and eligible/excluded counts;
- aggregate survival and mutation exclusion reasons;
- mutation representation policy;
- 173 ordered source mutation fields;
- raw-column to gene to derived-feature mapping;
- inclusive threshold and comparison semantics;
- number of rows used during selector fitting;
- per-gene fit prevalence;
- retained and excluded genes;
- retained derived names and fitted order;
- all-173-gene burden policy and `log1p` transformation;
- clinical transformation policy;
- ordered train-fitted standardized continuous feature names;
- ordered unscaled binary/one-hot feature names;
- raw and transformed feature counts; and
- forbidden-feature guard status.

The contracts remain serializable and independent of Streamlit and any survival-model library. They expose no patient IDs or patient-level feature values. Tracks A, B, and C carry no Track D mutation metadata.

## Leakage safeguards

Task feature frames are built from explicit ordered allowlists. Final Track D names fail validation if they expose:

- `patient_id` or split fields;
- survival time or event targets;
- subtype targets or labels;
- eligibility fields or reason metadata;
- raw `*_mut` annotation columns;
- mRNA features; or
- internal row metadata.

Derived `*_mut_present` predictors are explicitly permitted. Track B remains clinical plus exactly 489 mRNA predictors and contains zero mutation predictors.

## Canonical verification

Read-only canonical verification extends the existing R4 gate with Track D. It:

1. verifies R2/R3 readiness and captures canonical hashes;
2. calculates task-specific eligibility;
3. fits each preprocessor only on eligible locked-training rows;
4. transforms eligible validation/test rows without changing fitted state;
5. validates final feature names and typed metadata;
6. confirms Track D uses 173 source mutation fields and threshold `0.05`;
7. compares the full-training selected set with R4D-P0 evidence;
8. verifies the currently observed 27 retained genes and 44 transformed features as evidence only;
9. verifies Track B still contains zero mutation predictors; and
10. confirms canonical raw/prepared hashes remain unchanged.

Canonical evidence assertions are integration alarms for the currently committed dataset. They do not become selector defaults or production branch conditions.

## Aggregate-only Streamlit integration

The Data / Cohort readiness section is minimally extended to render four task cards and identify Track D mutation preprocessing as ready only when canonical verification succeeds. It may display aggregate eligibility and retained-feature counts from the report contract. It does not display patient-level mutation matrices, annotations, predictions, model scores, or survival outputs.

## Testing strategy

R4D is implemented test-first. Synthetic tests cover mutation parsing, invalid/missing handling, the inclusive 5% boundary, transform-time selection stability, fold-local set variability, all-gene burden, scaling separation, eligibility, exact feature names, leakage, fresh factory behavior, cloneability, and determinism. Existing R4 tests protect Tracks A, B, and C.

Canonical integration tests verify the current 173-source, 27-retained, 44-output evidence; Track D split eligibility; R4D-P0 agreement; Track B's zero mutation predictors; immutable hashes; and aggregate UI readiness. Tests do not require future CV folds to retain 27 genes.

## Dependencies

R4D uses the existing runtime dependencies: Python, pandas, NumPy, scikit-learn, Streamlit, and pytest for development verification. It adds no survival-analysis, model-runtime, explainability, or deep-learning dependency.

## Documentation

R4D updates README, architecture, data, API contracts, preprocessing, testing, limitations, changelog, implementation log, model integration/training boundaries, and aggregate user-flow documentation. A dedicated Track D preprocessing document records the representation, selector, burden, scaling groups, eligibility, evidence-versus-constant boundary, and future penalized-Cox handoff.

## Completion gate

Completion requires focused R4D tests, existing R4 and R4D-P0 tests, the full pytest suite, compile and dependency checks, canonical preprocessing smoke verification, selector/burden/eligibility evidence, Track isolation checks, cloneability and determinism checks, canonical hash verification, Git diff/status review, and Streamlit health plus desktop/narrow-layout checks because readiness UI changes.

R4D stops with preprocessing inputs ready for a later explicitly approved Track D modeling increment. It does not start model training.
