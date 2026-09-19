# R8 prognostic genomic feature analysis

R8 is a read-only analysis of the frozen R6 Track B penalized Cox model. It does not fit, refit, tune, select, or compare models. The trusted source is `artifacts/models/track_b/r6-track-b-v1/`, loaded only after its canonical path, tracked trust anchors, metadata, feature contract, and SHA-256 checksums verify.

## Frozen feature boundary

The R6 model has 80 encoded inputs. R8 excludes all 12 encoded clinical inputs and analyzes exactly the remaining 68 genomic coefficients:

- 50 train-standardized expression features;
- 18 unscaled binary mutation-presence features derived by the existing R4D annotation contract; and
- 0 clinical features.

The ordered raw-to-model mapping is persisted in `metadata.json`. Expression names are unchanged; each mutation annotation field `*_mut` maps to its fitted `*_mut_present` model feature.

## Coefficient contract

`COEF_EPS` is frozen at `1e-6`. A coefficient is active only when `abs(beta) > COEF_EPS`; values exactly at either boundary are effectively zero. Direction is higher modeled hazard for `beta > COEF_EPS`, lower modeled hazard for `beta < -COEF_EPS`, and effectively zero otherwise.

All 68 features remain in the canonical table. Ranking uses descending `abs_beta`, then frozen genomic order for exact ties. The current frozen R6 evidence contains 24 active and 44 effectively-zero coefficients. These counts are derived evidence, not selectors or production constants.

Lifelines standard errors, 95% intervals, z statistics, p-values, and negative-log2 p-values are preserved as model-reported descriptive fields. They do not drive ranking, activity, direction, filtering, or report emphasis. Penalization means these summaries must not be treated as an independent discovery or confirmatory biomarker analysis.

## Artifacts and verification

The canonical aggregate-only bundle is `artifacts/analysis/r8-prognostic-features-v1/` and contains the complete 68-row CSV, metadata, aggregate summary, report, independent 30-check audit, and checksum manifest. It contains no model pickle, preprocessor pickle, source rows, patient identifiers, durations, events, predictions, or row-level risks.

Run read-only verification with:

```powershell
.\.venv\Scripts\python.exe scripts/verify_prognostic_feature_artifacts.py --bundle artifacts/analysis/r8-prognostic-features-v1 --source-bundle artifacts/models/track_b/r6-track-b-v1
```

The audit is generated from explicit full-suite evidence with:

```powershell
.\.venv\Scripts\python.exe scripts/audit_prognostic_features.py --bundle artifacts/analysis/r8-prognostic-features-v1 --source-bundle artifacts/models/track_b/r6-track-b-v1 --full-test-suite-summary-file <pytest-output> --full-test-suite-passed
```

## Scientific limitations

Expression beta values are conditional model associations per one training-standardized expression unit. Mutation beta values compare binary mutation presence with absence. Because these inputs use different fitted scales, cross-type absolute-coefficient ranking is a model-scale association ranking, not biological unit equivalence.

R8 does not establish causality, mechanism, driver status, biomarker validity, treatment relevance, calibration, transportability, or clinical utility. External cohorts and separately approved biological analyses would be required for those questions.
