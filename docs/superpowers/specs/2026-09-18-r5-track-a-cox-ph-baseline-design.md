# R5 Track A Clinical-Only Cox PH Baseline Specification

## Status and scope

R5 implements the first fitted prognosis baseline for the biomedical application. It consumes the immutable R2 METABRIC package, the non-blocking R3 data-quality report, and the frozen R4 Track A eligibility and preprocessing contracts. It does not change canonical data, eligibility, Track A feature engineering, Tracks B/C/D, Streamlit result pages, or the locked test split.

The model is a transparent, unpenalized `lifelines.CoxPHFitter`. It is research and engineering evidence only, not a diagnostic, prognostic guarantee, treatment recommendation, or clinically validated system.

## Controlled dependency gate

Before model code is implemented, runtime constraints become:

- `lifelines==0.30.3`
- `pandas==2.3.3`
- existing `numpy>=2,<3`, `scikit-learn>=1.5,<2`, and `streamlit>=1.39,<2` constraints remain unchanged.

The project virtual environment must resolve those constraints, pass `pip check`, and pass the complete pre-R5 regression suite. Any dependency conflict or R2/R3/R4/R4D regression blocks R5 immediately. No unreleased lifelines revision or alternate survival library is permitted.

## Canonical population and split boundary

Track A uses the existing `evaluate_clinical_survival_eligibility` result and no R5-specific eligibility rule.

| Split | Eligible | R5 use |
|---|---:|---|
| Train | 1,332 | Fit preprocessing and Cox PH model |
| Validation | 285 | Transform, predict, and calculate the primary development C-index |
| Test | 286 | Identify only as locked and untouched; no transform, prediction, or metric |

The one non-positive-duration record stays excluded through `NON_POSITIVE_SURVIVAL_DURATION`. Imputable clinical missingness stays eligible. `NC` subtype labels do not affect Track A.

Final locked-test evaluation requires a later explicit approval after model specifications and common-cohort comparison policy are frozen.

## Predictor and preprocessing contract

R5 reuses `build_clinical_survival_preprocessor` and `select_task_features` without duplicating or modifying their policies. The approved raw predictors are:

1. `age_at_diagnosis`
2. `tumor_size`
3. `tumor_stage`
4. `lymph_nodes_examined_positive`
5. `er_status_measured_by_ihc`
6. `pr_status`
7. `her2_status`

The preprocessor is fitted on eligible training rows only and must produce the existing ordered 16-feature Track A matrix. Validation is transform-only. Test data are not transformed.

The model boundary rejects identifiers, split labels, duration/event targets, subtype fields, mRNA fields, mutation fields, eligibility fields, outcome-derived fields, and internal metadata. Duration and event remain separate inputs and cannot enter predictive `X`.

## Pre-fit matrix evidence

Before fitting, R5 records:

- row and transformed-feature counts;
- numeric matrix rank;
- zero-variance feature names;
- exact duplicate feature-column pairs;
- exact linear-dependency evidence when rank is below the transformed feature count;
- non-finite value evidence.

The R4 one-hot policy is not changed preemptively. If the 16-feature matrix is rank-deficient and fitting fails or raises a material convergence warning, the run stops with preserved evidence. R5 does not drop dummy columns, select reference levels, remove predictors, or add a penalizer.

## Model contract

The approved fitter configuration is:

```python
CoxPHFitter(
    baseline_estimation_method="breslow",
    penalizer=0.0,
    l1_ratio=0.0,
    strata=None,
    alpha=0.05,
)
```

No fallback is allowed. The fit adapter captures `ConvergenceWarning` and fitting exceptions. A material convergence warning, singularity, collinearity, separation, or numerical instability produces a failed R5 run and no successful model bundle.

The adapter accepts transformed predictors, ordered feature names, durations, and events as separate values. It may construct a temporary lifelines fit frame with reserved target columns, but those target columns do not belong to `X` or public feature metadata.

## Concordance contract

The canonical risk quantity is:

```python
risk_score = fitted_model.predict_log_partial_hazard(X)
```

Higher risk means higher modeled hazard. Harrell's concordance is calculated as:

```python
concordance_index(duration, -risk_score, event)
```

The negative sign converts higher-hazard scores into lifelines' higher-predicted-survival direction. R5 reports train C-index as a fit diagnostic and validation C-index as the primary development result. Metric metadata records score quantity, direction, negation, cohort counts, event/censor counts, and cohort fingerprint.

## Proportional-hazards diagnostics

R5 runs the training-cohort diagnostic:

```python
proportional_hazard_test(
    fitted_model,
    training_frame,
    time_transform="rank",
)
```

Each transformed feature receives its test statistic, p-value, threshold `0.05`, and flag state. Aggregate status is `PASSED`, `FLAGGED`, or `FAILED`. A flag is evidence only: R5 does not remove, transform, stratify, or interact a feature automatically. Diagnostic failure is surfaced explicitly rather than swallowed.

## Framework-independent contracts

`src/contracts/survival.py` defines serializable immutable contracts for:

- model configuration and run status;
- split-level cohort summaries;
- matrix diagnostics;
- concordance results;
- coefficient/hazard-ratio estimates and 95% confidence intervals;
- per-feature and aggregate PH diagnostics;
- runtime and dataset provenance;
- artifact records and complete Track A experiment results.

The result objects do not depend on Streamlit and contain no patient identifiers. A deterministic fingerprint over the ordered evaluation patient IDs supports proof of common-cohort evaluation without exposing the identifiers.

## Artifact bundle

Successful runs write a versioned local bundle beneath:

```text
artifacts/models/track_a/<experiment_id>/
├── experiment.json
├── metrics.json
├── coefficients.csv
├── ph_diagnostics.csv
├── preprocessor.pkl
├── cox_model.pkl
└── checksums.sha256
```

`preprocessor.pkl` and `cox_model.pkl` are trusted local artifacts, are ignored by Git, and must never be loaded from untrusted sources. JSON/CSV/checksum evidence may be retained under the repository's reproducible-results convention. Every artifact record includes its SHA-256 digest. Runtime metadata records Python, lifelines, pandas, NumPy, SciPy, scikit-learn, Git commit, canonical dataset hashes, and manifest identity.

## Future common-cohort evaluation

The fitted bundle supports evaluation on a supplied aligned subset without retraining. Later Track A/B/D comparison code will intersect eligibility by patient ID internally, evaluate each fitted model on identical rows, and publish only aggregate counts and a cohort fingerprint. R5 does not implement B/D models or C-index deltas.

## UI boundary

R5 adds no Streamlit result UI. Existing Survival Analysis and Model Comparison pages remain pending until the later UI milestone. No patient-level prediction, individual survival curve, prognosis, treatment recommendation, or clinical decision support is produced.

## Verification gate

R5 completion requires:

- controlled dependency resolution and `pip check`;
- pre-model full regression after the pandas compatibility change;
- focused contract, matrix, metric, adapter, diagnostic, artifact, and orchestration tests developed red-green;
- canonical fit using only the locked train split;
- train and validation metrics only;
- test-untouched evidence;
- artifact checksum and trusted round-trip verification;
- full pytest, compile check, dependency check, and `git diff --check`;
- unchanged canonical raw/prepared/manifest hashes and unchanged Track B/C/D behavior.

Any approved stop condition ends the increment with evidence and without a model-contract workaround.

## R5A approved reference-category remedy

The first canonical R5 fit was attempted exactly as specified and stopped. Its 1,332-by-16 training matrix had rank 13, no zero-variance or duplicate columns, and no non-finite values. Lifelines raised a singular-matrix convergence failure. The structural cause was four complete one-hot groups whose columns each sum to the all-ones vector, creating three exact dependencies. This failure remains part of the audit trail.

R5A changes categorical encoding for Track A only. Track B keeps its existing full clinical one-hot representation, Track C remains mRNA-only, and Track D keeps its existing full clinical one-hot plus mutation representation. The fixed Track A references are:

| Raw variable | Omitted reference |
|---|---|
| `tumor_stage` | `1` |
| `er_status_measured_by_ihc` | `Negative` |
| `pr_status` | `Negative` |
| `her2_status` | `Negative` |

The references were selected and frozen from train-only evidence; they are never chosen dynamically from validation or test frequencies. `tumor_stage=Unknown` remains an encoded canonical category. Missingness handling, train-only imputation, seven raw predictors, eligibility, and event coding remain unchanged.

The fitted preprocessor derives the output count and feature order. The expected canonical count is approximately 12 but is not a production constant. Before Cox fitting, the training matrix must be finite and full column rank. Diagnostics additionally record condition number, zero-variance columns, exact duplicates, and linear dependencies. Any remaining rank deficiency stops before fitting without penalization or automatic feature removal.

Every encoded categorical output records its raw variable, represented category, omitted reference category, and derived feature name. The reference itself has no coefficient or hazard ratio; it is only the comparison baseline. In particular, `tumor_stage=4` remains present despite seven training observations, and its coefficient, standard error, confidence interval, and convergence evidence are reported without an automatic remedy.

After full-rank verification, R5A retries the identical unpenalized Cox configuration and preserves all original train/validation/test, C-index, PH-diagnostic, artifact, and research-only boundaries. The held-out test split remains untransformed, unpredicted, and unscored.
