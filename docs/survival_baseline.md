# R5A clinical-only Cox PH baseline

## Purpose and boundary

R5A establishes a transparent clinical-only development baseline for future same-patient comparison with genomic survival tracks. It is a research/educational experiment, not a diagnostic, treatment, or clinical prognosis system. It does not populate Streamlit results, produce patient-specific output, fit Track B/D, or evaluate the held-out test split.

## Cohorts

The immutable manifest and Track A survival eligibility define:

| Split | Eligible | Events | Censored | R5A use |
|---|---:|---:|---:|---|
| Train | 1,332 | 760 | 572 | Fit preprocessing and Cox model |
| Validation | 285 | 168 | 117 | Transform, predict, and compute development C-index |
| Test | 286 | not inspected for R5A modeling | not inspected for R5A modeling | Count only; not transformed, predicted, or scored |

## Reference-category correction

The first approved attempt retained every one-hot category. Its 16-column training matrix had rank 13 and the unpenalized Cox fit stopped on a singular matrix. No penalizer, dropped predictor, or fallback estimator was introduced.

R5A uses these train-supported references only for Track A:

| Variable | Reference | Emitted comparisons |
|---|---|---|
| Tumor stage | `1` | `2`, `3`, `4`, `Unknown` |
| ER status measured by IHC | `Negative` | `Positive` |
| PR status | `Negative` | `Positive` |
| HER2 status | `Negative` | `Positive` |

`Unknown` remains a real tumor-stage category. The two original-value missing indicators remain unchanged. Tracks B and D preserve full-category encoding.

## Frozen estimator

- `lifelines.CoxPHFitter`
- `baseline_estimation_method="breslow"`
- `penalizer=0.0`
- `l1_ratio=0.0`
- `strata=None`
- `alpha=0.05`

The training matrix has 12 features, rank 12, condition number 966.312676, and no zero-variance, duplicate, or exact linear-dependency evidence. The fit converged with no convergence warnings.

## Development evidence

Harrell C-index uses log partial hazard as risk and negates it only when passed to `lifelines.utils.concordance_index`:

- training: 0.671466;
- validation: 0.650696;
- test: not calculated.

The rank-based proportional-hazards test at `p < 0.05` flagged age at diagnosis, Stage 2, Stage 3, ER-positive, and PR-positive. These findings did not trigger automatic feature removal, transformation, interaction, or stratification.

Stage 4 was retained. Its coefficient is 0.507871, hazard ratio 1.661750, standard error 0.434163, and 95% hazard-ratio interval 0.709586–3.891581. This wide interval is reported as imprecision, not hidden or treated as a reason for an unapproved model change.

## Artifacts and reproduction

Run:

```powershell
.\.venv\Scripts\python.exe scripts/train_track_a.py --experiment-id r5a-track-a-baseline-v1
```

The bundle under `artifacts/models/track_a/<experiment-id>/` contains JSON/CSV evidence, SHA-256 checksums, and local `preprocessor.pkl`/`cox_model.pkl`. Pickle files are gitignored trusted local artifacts. Never load a pickle from an untrusted source. The command refuses to overwrite a non-empty experiment directory and applies no fallback after a rank or convergence stop.

## Remaining risks

The validation result is internal and has no held-out or external confirmation. PH flags require a separately approved scientific/modeling decision. No calibration, uncertainty analysis beyond coefficient intervals, time-dependent performance, clinical utility analysis, subgroup validation, or competing-risk treatment is implemented.
