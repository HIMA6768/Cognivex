# Model training

R5A implements the first predictive development baseline: clinical-only Track A Cox proportional hazards. It uses lifelines 0.30.3 `CoxPHFitter` with Breslow baseline estimation, `penalizer=0.0`, `l1_ratio=0.0`, no strata, and `alpha=0.05`. There is no automatic penalization, feature deletion, stratification, or fallback model.

The locked training population is 1,332 patients (760 events, 572 censored). Track-A-only encoding uses Stage 1 and Negative ER-IHC/PR/HER2 as references. The resulting 12-column matrix has rank 12, condition number 966.312676, no zero-variance columns, no duplicate columns, and no exact linear dependency. The unpenalized fit converged without a convergence warning.

Validation is transform/predict/evaluate only. R5 did not transform or score test.

R6 Track B reuses the exact seven raw clinical predictors and adds exactly 50 expression and 18 mutation annotation inputs. Its fitted pipeline emits 80 model features: 12 frozen R5 clinical outputs, 50 train-standardized expression values, and 18 deterministic binary mutation-presence values. The source mutation annotations remain unchanged.

Six predefined penalized `CoxPHFitter` configurations were fit on the 1,332-row training split. Validation C-index alone selected `penalizer=0.05`, `l1_ratio=0.5`. Candidate models never accessed test; only the frozen winner transformed and scored the 286-row test split once. Future Track D training and any cross-validation must package the complete applicable preprocessor with its estimator so learned preprocessing refits inside each training fold.

Run the frozen baseline with:

```powershell
.\.venv\Scripts\python.exe scripts/train_track_a.py --experiment-id <safe-id>
```

The command never overwrites a non-empty bundle. A rank/convergence stop emits evidence and applies no fallback.

Run a new non-overwriting Track B experiment with:

```powershell
.\.venv\Scripts\python.exe scripts/train_track_b.py --experiment-id <safe-id>
```

## R7 Track C classification

Track C uses exactly 50 selected expression predictors plus 18 selected mutation annotation fields and no clinical variables. The existing R4D parser maps accepted non-zero annotations to binary presence and zero to absence; source annotations remain unchanged. Logistic Regression and RBF SVM fit expression scaling on the 1,330-row eligible training split. Random Forest and Gradient Boosting retain the prepared expression values. Mutation indicators are never scaled.

The frozen candidates are Logistic Regression, Random Forest, Gradient Boosting, and RBF SVM with the approved deterministic configurations. Validation Macro-F1 alone selected Random Forest (0.771384). Candidate selection had no test input. After freezing the winner, one evaluation was performed on the 283 eligible test rows. Historical engineer pickle models were not loaded.
