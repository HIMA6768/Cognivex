# Track D mutation preprocessing

R4D prepares clinical-plus-mutation predictors for a future penalized Cox survival model. It is preprocessing only: no survival estimator, C-index, risk score, outcome-associated gene ranking, or patient prediction is produced.

## Source representation

Track D consumes the 173 ordered `*_mut` annotation fields declared in `feature_groups.json`. Trimmed string or numeric zero means no reported mutation; a finite nonzero value or non-empty annotation string means mutation reported. Blank/null values are missing, while boolean and non-finite representations are invalid. Missing and invalid values are excluded through stable Track D eligibility reasons and are never silently treated as absence.

Raw annotation identity never becomes magnitude. Derived predictors use deterministic names such as `pik3ca_mut_present`, and canonical CSV values are never rewritten.

## Fit-local selection

`MutationFrequencySelector` learns prevalence from only the rows supplied to `fit()` and retains genes with prevalence `>= 0.05`. `transform()` uses exactly that fitted set and does not recalculate prevalence. Therefore, future cross-validation must contain the complete Track D preprocessor and model inside each fold; different fold-training samples may correctly retain different genes.

The locked full-training partition currently retains 27 genes. That count and list are canonical integration evidence, not constants and not selector inputs.

## Mutation burden

`mutation_burden_log1p` is `log1p` of the number of reported mutations across all 173 source genes. It is independent of the frequency-selected set. Raw burden is not emitted as a second predictor.

## Clinical and scaling policy

Track D reuses the approved R4 clinical categories, train-only tumor-size median imputation, train-only ER-IHC most-frequent imputation, and exact original-value indicators.

Train-fitted standardized continuous outputs are:

- `age_at_diagnosis`
- `tumor_size`
- `lymph_nodes_examined_positive`
- `mutation_burden_log1p`

Unscaled outputs are every clinical one-hot variable, both missing indicators, and every selected binary `*_mut_present` variable. Fitted metadata records both ordered groups and validates that they form an exact, disjoint partition of final Track D features.

## Eligibility and leakage boundary

Track D uses the survival-valid population plus structurally valid mutation fields. `NC` has no effect, approved clinical missingness does not exclude a row, and mutation prevalence is not an eligibility rule. The canonical result is 1,332 train, 285 validation, and 286 test rows eligible (1,903 total), with the zero-duration validation row excluded by `NON_POSITIVE_SURVIVAL_DURATION`.

The final matrix contains only 16 transformed clinical variables, fit-selected mutation indicators, and standardized log1p burden. It excludes IDs, splits, outcomes, subtype labels, eligibility metadata, raw mutation strings, and all mRNA fields. The current full-training fit produces 44 outputs (16 + 27 + 1); 44 is evidence only, not a production constant.

## Future modeling boundary

A later approved Track D increment may place this preprocessor before a penalized Cox estimator and compare Tracks A, B, and D on the same eligible evaluation population. Model fitting, tuning, evaluation, and selection-frequency analysis are outside R4D.
