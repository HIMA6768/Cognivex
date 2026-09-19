# R6 Track B — Clinical + Genomic Survival Model

## Objective

Evaluate whether the explicit 68-feature genomic contract improves survival discrimination over the frozen seven-feature R5 clinical baseline. Track B was selected using validation performance only.

## Dataset and split

- Canonical prepared cohort: 1,904 patients
- Survival-eligible train: 1332 (760 events)
- Survival-eligible validation: 285 (168 events)
- Survival-eligible test: 286 (175 events)
- Duration: `overall_survival_months`
- Event: `overall_survival` (`1` = deceased/event; `0` = living/censored)

## Feature contract and preprocessing

- Frozen R5 clinical predictors: 7
- Explicit selected expression predictors: 50; standardized by a train-fitted `StandardScaler`
- Explicit selected mutation predictors: 18; existing R4D annotation semantics map absence `0` to 0 and valid non-zero annotations to 1
- Raw predictors: 75
- Encoded model features: 80
- Clinical imputation and reference-category encoding reuse the frozen R5 train-fitted contract
- Validation and test use transform-only preprocessing

## Validation leaderboard

| Order | Penalizer | L1 ratio | Status | Validation C-index |
|---:|---:|---:|---|---:|
| 1 | 0.05 | 0.0 | CONVERGED | 0.637373 |
| 2 | 0.10 | 0.0 | CONVERGED | 0.642822 |
| 3 | 0.05 | 0.5 | CONVERGED | 0.644544 |
| 4 | 0.10 | 0.5 | CONVERGED | 0.643138 |
| 5 | 0.05 | 1.0 | CONVERGED | 0.640361 |
| 6 | 0.10 | 1.0 | CONVERGED | 0.606756 |

Selected configuration: penalizer `0.05`, l1 ratio `0.5`.

## Track A versus Track B

| Split | Track A C-index | Track B C-index | Delta B - A |
|---|---:|---:|---:|
| Validation | 0.650696 | 0.644544 | -0.006152 |
| Test | 0.624983 | 0.640915 | 0.015932 |

Track B was selected using validation performance only. Candidate models were not evaluated on test; only the frozen validation winner received one final test evaluation.

## Limitations

- This research/educational result is not a clinical decision system.
- The selected genomic panel and regularization grid are predefined engineering inputs, not causal or biological evidence.
- Coefficients must not be interpreted as Track D biological conclusions.
- External validation and calibration remain out of scope.
