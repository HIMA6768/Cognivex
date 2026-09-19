# R6 Track B Clinical + Genomic Survival Design

## Objective

R6 measures whether exactly 50 selected expression features and 18 selected mutation-presence features improve survival discrimination over the frozen seven-feature R5 clinical Cox baseline. It trains and selects Track B using train and validation only, evaluates the frozen winner once on test, evaluates the already-fitted trusted R5 artifact on the identical validation/test cohorts, persists reproducible evidence, audits the result, and stops before R7/R8.

## Frozen authorities

- Active data: `data/metabric/prepared/METABRIC_prepared.csv` (1,904 rows, 693 columns).
- Locked manifest: `data/metabric/metadata/manifest.csv` (1,332/286/286).
- Survival: `overall_survival_months`; prepared `overall_survival=1` is event/deceased and `0` is living/censored. No inversion is allowed.
- Eligibility: the existing clinical-survival rule, yielding the same Track A/B cohorts.
- Clinical raw features, in order: `age_at_diagnosis`, `tumor_size`, `tumor_stage`, `lymph_nodes_examined_positive`, `er_status_measured_by_ihc`, `pr_status`, `her2_status`.
- Genomic names: committed `ai_handoff_data/v1/selected_features.txt`, partitioned into exactly 50 expression and 18 `_mut` names.
- Frozen R5 commit/artifacts remain unchanged. Historical engineer pickles are never loaded.

## Preprocessing

Track B accepts exactly 75 ordered raw predictors. Its clinical branch embeds `build_clinical_survival_preprocessor`, preserving R5 reference categories, train-fitted tumor-size/ER-IHC imputation, original-value missing indicators, and unscaled clinical values. Its expression branch fits one `StandardScaler` on the 50 training columns and transforms validation/test without fitting. Its mutation branch calls `classify_mutation_annotation`: trimmed numeric zero becomes `0`, valid non-zero annotation becomes `1`, and missing/boolean/non-finite malformed values fail. It learns no mutation statistics and emits 18 `_present` names. The expected encoded order is 12 clinical, 50 expression, and 18 mutation columns: 80 total.

Source annotation columns and canonical CSVs are immutable. Every transformed mutation value must belong to `{0, 1}`.

## Cohort and test isolation

Preparation loads all splits but keeps raw frames separate. Candidate selection receives train and validation only. It fits preprocessing on train once, transforms validation once, fits every candidate on train, and chooses the highest validation Harrell C-index with candidate declaration order as the deterministic tie-break. Test is transformed only by the finalization function after the winning configuration is frozen. Only the winner is scored on test.

The trusted local R5 preprocessor/model are loaded from `artifacts/models/track_a/r5a-track-a-baseline-v1/` only with the explicit trusted-pickle gate. They are not refitted. Their validation score must reproduce the frozen R5 metric on the identical cohort before R6 finalization; their test score is calculated once for the approved R6 comparison.

## Candidate grid

Use six predefined `CoxPHFitter` candidates with Breslow baseline, no strata, and alpha 0.05:

1. penalizer 0.05, l1_ratio 0.0
2. penalizer 0.10, l1_ratio 0.0
3. penalizer 0.05, l1_ratio 0.5
4. penalizer 0.10, l1_ratio 0.5
5. penalizer 0.05, l1_ratio 1.0
6. penalizer 0.10, l1_ratio 1.0

Material convergence warnings make that candidate failed; selection continues. If every candidate fails, R6 stops without test evaluation.

## Components

- `src/contracts/track_b.py`: feature, candidate, comparison, and experiment contracts.
- `src/preprocessing/track_b.py`: explicit feature loader, mutation transformer, and composite preprocessor.
- `src/modeling/track_b.py`: configurable penalized Cox adapter.
- `src/training/track_b.py`: canonical split preparation, validation-only selection, final test comparison, and reload evidence.
- `src/artifacts/track_b.py`: non-overwriting artifact persistence and report generation.
- `src/audit/track_b.py`: the required 25 deterministic audit checks.
- `scripts/train_track_b.py`: repository-root CLI for the one canonical run.

## Artifacts

Write `artifacts/models/track_b/r6-track-b-v1/` containing `metadata.json`, `metrics.json`, `feature_contract.json`, `validation_leaderboard.csv`, `report.md`, `audit.json`, `checksums.sha256`, and trusted-local `preprocessor.pkl`/`cox_model.pkl`. Pickles remain ignored; machine-readable aggregate evidence and report are committed. No patient identifiers or row-level predictions are persisted.

## Failure policy

Fail before fitting on data/checksum/split/feature/eligibility/event-contract mismatch, mutation parse failure, non-binary transformed mutations, non-finite matrices, missing trusted R5 artifacts, R5 validation mismatch, or all-candidate failure. Do not silently add fields, invert events, refit on holdouts, use test for selection, or fall back to engineer artifacts.

## Verification and stop

Tests cover feature counts/order, R4D mutation semantics, train-only fitting, event preservation, identical cohorts, validation-only selection, trusted artifact persistence/reload, metrics/report agreement, and all audit checks. Run focused tests, full pytest, compileall, pip check, diff check, and status. Commit R6 independently and stop before R7/R8, UI, inference, or deployment.
