# Model evaluation

R5A evaluates log partial hazard with Harrell's concordance index. Because lifelines' metric expects higher predicted scores to correspond to longer survival, the implementation supplies `-predict_log_partial_hazard(X)`. Synthetic tests cover perfect ordering, reversed ordering, ties, and censoring.

Canonical development evidence:

| Split | Rows | Events | Censored | C-index |
|---|---:|---:|---:|---:|
| Training | 1,332 | 760 | 572 | 0.671466 |
| Validation | 285 | 168 | 117 | 0.650696 |

R5A left test untouched. R6 subsequently loaded the frozen R5 artifact and evaluated Track A and Track B on identical eligible validation/test cohorts for the approved comparison.

| Track | Split | Rows | Events | Censored | C-index |
|---|---|---:|---:|---:|---:|
| A | Validation | 285 | 168 | 117 | 0.650696 |
| B | Validation | 285 | 168 | 117 | 0.644544 |
| A | Test | 286 | 175 | 111 | 0.624983 |
| B | Test | 286 | 175 | 111 | 0.640915 |

Track B minus Track A is -0.006152 on validation and +0.015932 on test. The mixed direction does not establish a generalizable genomic improvement. The values are internal development evidence, not external validation or clinical utility.

The rank-transformed proportional-hazards test at `p < 0.05` flagged age at diagnosis, Stage 2, Stage 3, ER-positive, and PR-positive. The flags are diagnostic evidence only; no feature was removed, transformed, stratified, or interacted. Stage 4 remained finite but imprecise (HR 1.661750; 95% CI 0.709586–3.891581).

Future A/B/D comparison must use identical eligible patient subsets. Future subtype evaluation should include accuracy, macro precision, macro recall, macro F1, weighted F1, per-class metrics, and a confusion matrix where supported by the verified labels.
