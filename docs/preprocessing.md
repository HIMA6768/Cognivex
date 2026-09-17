# R4 leak-safe preprocessing

R4 provides three separate, fresh, unfitted sklearn-compatible preprocessors. They are engineering inputs for later model increments, not fitted predictive models.

## Task boundaries

| Track | Task | Predictors | R4 transformation |
|---|---|---|---|
| Track A | `clinical_survival` | Seven approved clinical fields | Train-only tumor-size median and ER-IHC mode imputation, schema-ordered one-hot encoding, no numeric scaling |
| Track B | `clinical_mrna_survival` | Track A fields plus 489 ordered mRNA features | Track A clinical transform plus train-only `StandardScaler` on mRNA |
| Track C | `subtype_classification` | 489 ordered mRNA features | Preserve canonical METABRIC expression Z-scores without additional R4 scaling |

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
- The zero-duration record is excluded from A/B with `NON_POSITIVE_SURVIVAL_DURATION` but remains eligible for C.
- `NC` does not affect A/B and excludes six records only from C.
- Missing tumor size or ER-IHC alone does not exclude a survival row because the approved pipeline handles those values.

The canonical results are:

| Task | Train eligible | Validation eligible | Test eligible | Total eligible | Excluded |
|---|---:|---:|---:|---:|---:|
| Track A | 1,332 | 285 | 286 | 1,903 | 1 |
| Track B | 1,332 | 285 | 286 | 1,903 | 1 |
| Track C | 1,330 | 285 | 283 | 1,898 | 6 |

## Feature ordering and safeguards

Track A emits 16 features: three numeric values, schema-ordered categorical expansions, and the two named missingness indicators. Track B appends all 489 mRNA features in `feature_groups.json` order for 505 transformed features. Track C emits the same 489 genes in that order.

The feature selector and fitted-name guard reject identifiers, split metadata, survival targets, subtype targets, eligibility metadata, and all `*_mut` fields. Mutation annotations remain untouched in the canonical dataset and are excluded from all R4 matrices. No gene filtering or selection occurs.

## Fit policy

At the locked holdout level, only eligible training rows may call `fit()` or `fit_transform()`. Validation and test call `transform()` only. Canonical verification snapshots fitted state before holdout transformation and confirms that state remains unchanged.

Future cross-validation must receive a complete preprocessor-plus-model pipeline. Preprocessing must fit independently inside each training fold; it must not be fitted once on all 1,332 locked-training records before cross-validation.

## Phase boundary

R4 does not fit Cox PH, Coxnet, or a subtype classifier. R5 may consume Track A, R6 may consume Track B, and R7 may consume Track C. If R7 chooses a scale-sensitive classifier, scaling belongs inside that future classifier pipeline and must fit independently within training/CV folds.
