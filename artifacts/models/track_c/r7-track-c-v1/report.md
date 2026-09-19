# R7 Track C — Molecular Subtype Classification

## Objective

Classify six dataset-confirmed molecular subtype labels from the frozen 68-feature genomic contract. The selected model is **Random Forest** (`random_forest`) because it achieved the highest validation Macro-F1 under the approved deterministic tie rule.

## Dataset and eligibility

- Target: `pam50_+_claudin-low_subtype`
- Train: 1330 eligible; 2 NC excluded
- Validation: 285 eligible; 1 NC excluded
- Test: 283 eligible; 3 NC excluded
- NC, missing targets, and unsupported targets are excluded only from Track C.

## Contract

- Expression predictors: 50
- Mutation-presence predictors: 18, derived with existing R4D annotation semantics
- Clinical predictors: 0
- Target classes: Basal, Her2, LumA, LumB, Normal, claudin-low
- NC, missing targets, and unsupported targets are excluded only from Track C.

## Validation leaderboard

| Order | Model | Macro F1 | Weighted F1 | Accuracy | Balanced accuracy |
|---:|---|---:|---:|---:|---:|
| 1 | Logistic Regression | 0.701404 | 0.721689 | 0.719298 | 0.717110 |
| 2 | Random Forest | 0.771384 | 0.795845 | 0.796491 | 0.767622 |
| 3 | Gradient Boosting | 0.744275 | 0.779858 | 0.785965 | 0.723878 |
| 4 | RBF SVM | 0.741258 | 0.764820 | 0.764912 | 0.751422 |

## Final frozen-winner test metrics

- Macro F1: 0.734176
- Weighted F1: 0.748642
- Accuracy: 0.749117
- Balanced accuracy: 0.719373

### Per-class test metrics

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| Basal | 0.923077 | 0.774194 | 0.842105 | 31 |
| Her2 | 0.638889 | 0.718750 | 0.676471 | 32 |
| LumA | 0.760000 | 0.760000 | 0.760000 | 100 |
| LumB | 0.701299 | 0.830769 | 0.760563 | 65 |
| Normal | 0.611111 | 0.458333 | 0.523810 | 24 |
| claudin-low | 0.923077 | 0.774194 | 0.842105 | 31 |

### Confusion matrix

Rows are actual classes and columns are predicted classes in the frozen order.

| Actual \ Predicted | Basal | Her2 | LumA | LumB | Normal | claudin-low |
|---|---:|---:|---:|---:|---:|---:|
| Basal | 24 | 4 | 1 | 1 | 0 | 1 |
| Her2 | 1 | 23 | 1 | 7 | 0 | 0 |
| LumA | 0 | 3 | 76 | 14 | 7 | 0 |
| LumB | 0 | 3 | 8 | 54 | 0 | 0 |
| Normal | 0 | 3 | 8 | 1 | 11 | 1 |
| claudin-low | 1 | 0 | 6 | 0 | 0 | 24 |

The test set was not used for model selection. Only the frozen validation winner received final test evaluation.

## Limitations

- This is a research/educational prototype, not a diagnostic or clinical decision system.
- Results are specific to the locked internal METABRIC split and require external validation.
- Classification performance does not establish biological causality or feature importance.
