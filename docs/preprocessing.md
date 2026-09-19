# R4/R4D leak-safe preprocessing

R4/R4D provide four separate, fresh, unfitted sklearn-compatible preprocessors. They are engineering inputs for later model increments, not fitted predictive models.

## Task boundaries

| Track | Task | Predictors | R4 transformation |
|---|---|---|---|
| Track A | `clinical_survival` | Seven approved clinical fields | Train-only tumor-size median and ER-IHC mode imputation, fixed reference-category encoding for R5A, no numeric scaling |
| Track B | `clinical_mrna_survival` | Seven clinical fields plus 489 ordered mRNA features | Full-category clinical encoding plus train-only `StandardScaler` on mRNA |
| Track C | `subtype_classification` | 489 ordered mRNA features | Preserve canonical METABRIC expression Z-scores without additional R4 scaling |
| Track D | `clinical_mutation_survival` | Seven clinical fields plus 173 mutation annotations | Scale continuous clinical/log1p burden; leave one-hot, missing indicators, and fit-selected binary mutation presence unscaled |

Track C target normalization is separate from predictor preprocessing. Source labels such as `LumA` are mapped through `subtype_labels.json` to the six canonical classes. `NC` maps to no supervised target and is excluded through Track C eligibility; neither raw nor normalized subtype labels enter X.

## Clinical missingness

R4 records original nullness before imputation using the contractual names:

- `tumor_size_was_missing`
- `er_status_measured_by_ihc_was_missing`

`tumor_size` uses the median learned from the applicable training rows. ER-IHC uses the most frequent category learned from those rows. Validation and test rows cannot alter either statistic. Missingness in another clinical predictor fails clearly because no other imputation policy is approved. `Unknown` is a legitimate tumor-stage category.

## Eligibility

Eligibility is task-specific and row-aligned without storing patient identifiers in public metadata.

- Tracks A/B require a present, numeric, finite, positive survival duration; a canonical event in `{0, 1}`; and a valid locked split. Track B additionally requires all expected mRNA values to be numeric and finite.
- Track C requires a subtype label that maps to one of the six canonical classes plus valid mRNA values. It does not inspect survival outcomes.
- The zero-duration record is excluded from A/B/D with `NON_POSITIVE_SURVIVAL_DURATION` but remains eligible for C.
- `NC` does not affect A/B/D and excludes six records only from C. Track D adds mutation structural validity without using mutation prevalence as row eligibility.
- Missing tumor size or ER-IHC alone does not exclude a survival row because the approved pipeline handles those values.

The canonical results are:

| Task | Train eligible | Validation eligible | Test eligible | Total eligible | Excluded |
|---|---:|---:|---:|---:|---:|
| Track A | 1,332 | 285 | 286 | 1,903 | 1 |
| Track B | 1,332 | 285 | 286 | 1,903 | 1 |
| Track C | 1,330 | 285 | 283 | 1,898 | 6 |
| Track D | 1,332 | 285 | 286 | 1,903 | 1 |

## Feature ordering and safeguards

Track A emits 12 features: three numeric values; Stage 2, Stage 3, Stage 4, and `Unknown` compared with Stage 1; positive ER-IHC, PR, and HER2 compared with each Negative reference; and the two named missingness indicators. Track B deliberately retains full-category clinical encoding and appends all 489 mRNA features in `feature_groups.json` order for 505 transformed features. Track C emits the same 489 genes in that order. Track D also retains its prior full-category clinical branch and 44 current full-training outputs.

The feature selector and fitted-name guard reject identifiers, split metadata, survival targets, subtype targets, eligibility metadata, and raw `*_mut` fields from final matrices. Mutation annotations remain untouched in the canonical dataset. Tracks A–C exclude mutations; Track D converts them to fit-selected `*_mut_present` indicators and all-gene log1p burden. See [mutation_preprocessing.md](mutation_preprocessing.md).

## Fit policy

At the locked holdout level, only eligible training rows may call `fit()` or `fit_transform()`. Validation and test call `transform()` only. Canonical verification snapshots fitted state before holdout transformation and confirms that state remains unchanged.

Future cross-validation must receive a complete preprocessor-plus-model pipeline. Preprocessing—including Track D's frequency selector—must fit independently inside each training fold; it must not be fitted once on all 1,332 locked-training records before cross-validation.

## R5A consumption boundary

R5A consumes Track A in an unpenalized Cox PH development baseline. It fits on 1,332 locked training patients, evaluates 285 eligible validation patients, and leaves all 286 test patients untransformed and unscored. R6 may consume Track B, and R7 may consume Track C. If R7 chooses a scale-sensitive classifier, scaling belongs inside that future classifier pipeline and must fit independently within training/CV folds.

## Data / Cohort readiness presentation

The Data / Cohort page derives `PREPROCESSING_READY` from the read-only canonical R4 verification contract rather than from UI constants. It displays aggregate Track A/B/C eligibility, missingness-indicator counts, mRNA feature counts, zero-duration and NC exclusion counts, mutation-predictor count, and forbidden-feature guard result. This status coexists with R3 `DATA_QUALITY_READY_WITH_WARNINGS`: R3 warnings describe immutable source-data properties, while R4 readiness describes completed downstream preprocessing policies.
