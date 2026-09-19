# Model evaluation

R5A evaluates log partial hazard with Harrell's concordance index. Because lifelines' metric expects higher predicted scores to correspond to longer survival, the implementation supplies `-predict_log_partial_hazard(X)`. Synthetic tests cover perfect ordering, reversed ordering, ties, and censoring.

Canonical development evidence:

| Split | Rows | Events | Censored | C-index |
|---|---:|---:|---:|---:|
| Training | 1,332 | 760 | 572 | 0.671466 |
| Validation | 285 | 168 | 117 | 0.650696 |

The 286-row test split has no transformation, prediction, or metric in R5A. These values are development evidence, not external validation or clinical utility.

The rank-transformed proportional-hazards test at `p < 0.05` flagged age at diagnosis, Stage 2, Stage 3, ER-positive, and PR-positive. The flags are diagnostic evidence only; no feature was removed, transformed, stratified, or interacted. Stage 4 remained finite but imprecise (HR 1.661750; 95% CI 0.709586–3.891581).

Future A/B/D comparison must use identical eligible patient subsets. Future subtype evaluation should include accuracy, macro precision, macro recall, macro F1, weighted F1, per-class metrics, and a confusion matrix where supported by the verified labels.
