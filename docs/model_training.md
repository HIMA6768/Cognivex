# Model training

R5A implements the first predictive development baseline: clinical-only Track A Cox proportional hazards. It uses lifelines 0.30.3 `CoxPHFitter` with Breslow baseline estimation, `penalizer=0.0`, `l1_ratio=0.0`, no strata, and `alpha=0.05`. There is no automatic penalization, feature deletion, stratification, or fallback model.

The locked training population is 1,332 patients (760 events, 572 censored). Track-A-only encoding uses Stage 1 and Negative ER-IHC/PR/HER2 as references. The resulting 12-column matrix has rank 12, condition number 966.312676, no zero-variance columns, no duplicate columns, and no exact linear dependency. The unpenalized fit converged without a convergence warning.

Validation is transform/predict/evaluate only. The test split remains held out and is represented only by its aggregate count of 286. Future Track B/D training and any cross-validation must package the complete applicable preprocessor with its estimator so learned preprocessing refits inside each training fold.

Run the frozen baseline with:

```powershell
.\.venv\Scripts\python.exe scripts/train_track_a.py --experiment-id <safe-id>
```

The command never overwrites a non-empty bundle. A rank/convergence stop emits evidence and applies no fallback.
