# R8 Prognostic Genomic Feature Analysis Design

## Purpose

R8 is a read-only, post-hoc analysis of the frozen R6 Track B penalized Cox model. It answers one bounded question: within that fitted model, which of the 68 approved genomic predictors have the strongest model-associated relationships with modeled survival hazard?

R8 extracts the frozen coefficients, derives hazard ratios and deterministic rankings, preserves carefully labeled model-reported summary values, and writes aggregate analysis evidence. It does not fit, refit, tune, select, score, or otherwise change a model. It does not establish biological causality, clinical utility, or validated biomarkers.

## Roadmap clarification

The authoritative roadmap definition is:

> R8 = prognostic genomic feature association and importance analysis derived from the already-frozen R6 Track B penalized Cox model.

R8 is not mutation-enhanced survival training, a Track D Cox model, another clinical-plus-genomic model, or R7 classifier explanation. Earlier wording that assigns biological support or a new Track D survival model to R8 is superseded. Track D preprocessing remains preserved, but Track D model fitting is a separate unapproved future increment.

Repository wording requiring later cleanup is recorded rather than changed in this design-only commit:

- `docs/architecture.md` currently says `R8 gene importance and biological support`; the biological-support portion is outside the approved R8 boundary.
- `cognivex_ml/README.md`, `cognivex_ml/docs/data_strategy.md`, and `cognivex_ml/results/track_d_report.md` call engineer coefficient output Track D. They are imported reference material, not the active Cognivex roadmap.
- `docs/model_integration.md` and `docs/mutation_preprocessing.md` defer a future Track D model. That deferred work is not part of R8.

## Immutable authorities

R5, R6, and R7 remain frozen at commits `93f669cf7638a09bcff0434f9f93590aa0c552e1`, `49a8414c1aa828c07cfa9f9dd207a2bdf311b078`, and `97e6434634c3391acbd6e5e50dca316bef4ad6fb`, respectively. R8 reads only the canonical R6 bundle at `artifacts/models/track_b/r6-track-b-v1/` and repository source needed to verify its contract.

The inspected R6 authorities are:

- R6 implementation commit: `49a8414c1aa828c07cfa9f9dd207a2bdf311b078`.
- R6 artifact-generation commit recorded by its metadata: `fde3ecd4646ee7f28fca5378335277d950e7d87d`.
- Model adapter: `src.modeling.track_b.PenalizedCoxPHAdapter`.
- Fitted model: `lifelines.CoxPHFitter`, Breslow baseline, `penalizer=0.05`, `l1_ratio=0.5`, `alpha=0.05`.
- Model artifact SHA-256: `5d312d905974772ad0967ba8dbd47bce7de81dc3cca5fdee54f8ad259a3d86f2`.
- Preprocessor artifact SHA-256: `d23c26e85ef30b1d85c87055b2e824ecb0624af7c3ddedceacd75c5bfbe6acb5`.
- Feature-contract SHA-256: `97888b7cbb655d542a4a3cafc42bdfe1d65e267d95cc8e84f125d2a4003fff27`.
- Prepared-data SHA-256 inherited from R6: `e18275dac2b8b11d158093785816ae04d3b2466217d5af47a6290e5927146c29`.
- Manifest SHA-256 inherited from R6: `d4c884a92a988d9352e1da3bb1bbcc02037dad96a31991779c4589cb9e`.
- Frozen validation C-index: `0.6445444319460067`.
- Frozen test C-index: `0.6409151636606546`.

The R6 checksum manifest currently verifies all eight covered bundle files. The adapter feature order, fitted-preprocessor feature order, `CoxPHFitter.params_` index, and `CoxPHFitter.summary` index are all the same 80-name sequence. R8 treats these agreements as required source-validation checks, not assumptions.

R8 must never call `fit`, `fit_transform`, `CoxPHFitter.fit`, an R5/R6/R7 training function, or an engineer training entrypoint. It does not load the prepared CSV or manifest rows; dataset and manifest hashes are inherited from verified R6 lineage.

## Approaches considered

### Approach A — direct analysis of the frozen R6 coefficients

Verify and load the trusted R6 model and preprocessor, map the explicit persisted genomic contract into the fitted 80-feature order, and derive all R8 evidence from `params_` and `summary`.

Benefits: answers the approved question directly, preserves the locked model and its evaluation discipline, requires no patient rows, adds no model-selection surface, and uses Cox coefficients on their actual model scale. Limitations: conclusions are conditional on one penalized model, coefficient magnitudes depend on each predictor's transformed scale, and model-reported inferential values need conservative labeling.

### Approach B — fit a genomic-only or mutation-enhanced survival model

This could answer a different scientific question or exercise Track D preprocessing, but it would introduce new fitting, feature/model selection, evaluation, and leakage risks. It would not explain the frozen R6 model and directly violates the approved R8 contract.

### Approach C — permutation or SHAP-style post-hoc importance

These methods can quantify prediction sensitivity, including nonlinear behavior in other model families, but they require patient-level transformed data, additional methodological choices, correlated-feature caveats, and potentially new dependencies. They answer a different importance question than coefficient association and are not required for this linear Cox model.

### Selected approach

Approach A is selected. Repository inspection found no ambiguity or defect that prevents exact coefficient extraction. Approaches B and C remain outside R8 unless separately approved.

## Selected architecture

The analysis is a checksum-gated pipeline with five stages:

1. Verify the canonical R6 bundle path, frozen tracked source, and every checksum before deserializing a pickle.
2. Load only the verified trusted local R6 `preprocessor.pkl` and `cox_model.pkl` through `src.artifacts.survival.load_trusted_pickle(..., trusted=True)`.
3. Validate adapter type, fitted state, selected hyperparameters, persisted feature contract, preprocessor order, adapter order, coefficient index, and summary index.
4. Build the explicit 68-row genomic mapping, extract coefficients and model-reported summary values, derive safe deterministic values, and rank all rows.
5. Persist a non-overwriting aggregate analysis bundle, then run the independent 30-check audit and read-only bundle verification.

R8 does not transform source rows, generate risk scores, evaluate patients, or import training modules. The source R6 artifacts remain unchanged before and after analysis.

## R6 source and artifact lineage

The source bundle consists of:

- `artifacts/models/track_b/r6-track-b-v1/cox_model.pkl`
- `artifacts/models/track_b/r6-track-b-v1/preprocessor.pkl`
- `artifacts/models/track_b/r6-track-b-v1/feature_contract.json`
- `artifacts/models/track_b/r6-track-b-v1/metadata.json`
- `artifacts/models/track_b/r6-track-b-v1/metrics.json`
- `artifacts/models/track_b/r6-track-b-v1/validation_leaderboard.csv`
- `artifacts/models/track_b/r6-track-b-v1/report.md`
- `artifacts/models/track_b/r6-track-b-v1/audit.json`
- `artifacts/models/track_b/r6-track-b-v1/checksums.sha256`

Before pickle loading, R8 must establish all of the following:

- the bundle resolves to the fixed repository-relative path;
- the committed checksum manifest and tracked R6 files match frozen R6 commit `49a8414c1aa828c07cfa9f9dd207a2bdf311b078`;
- every file named by `checksums.sha256` matches its expected digest;
- metadata identifies `r6-track-b-v1`, Track B, and `clinical_genomic_survival`;
- metadata freezes `penalizer=0.05`, `l1_ratio=0.5`, validation-only selection, and one winner-only test evaluation;
- the feature contract contains 7 clinical, 50 expression, 18 mutation, 75 raw, and 80 model fields;
- the loaded objects have the expected repository-defined adapter/preprocessor types and fitted state.

Any mismatch blocks R8 before coefficient extraction. The checksum file is the committed trust anchor for ignored local pickles; a locally supplied pickle with an unrecognized digest is prohibited even if it deserializes.

## Genomic feature contract

R8 analyzes exactly 68 genomic predictor concepts in frozen R6 contract order:

- 50 expression features from `feature_contract.json.expression_features`;
- 18 mutation annotation source features from `feature_contract.json.mutation_features`;
- 0 clinical features.

The full 68-feature table is canonical. The activity threshold classifies rows but never removes them. No feature is discovered by dtype, numeric status, prefix scanning, coefficient-name appearance, or current dataset content.

The frozen genomic order is the persisted 50-expression order followed by the persisted 18-mutation order. This same order supplies the tie-break index and is stored in R8 metadata.

## Encoded-feature mapping

The inspected 80-feature R6 model order is unambiguous:

- positions 1–12: encoded clinical outputs;
- positions 13–62: the 50 expression names, unchanged;
- positions 63–80: the 18 transformed mutation-presence names.

Mapping rules are exact:

- expression raw name `x` maps to model name `x`;
- mutation raw name `x_mut` maps to model name `x_mut_present`, using the fitted R6 transformer's public naming contract.

Implementation must construct those mappings from the persisted R6 expression and mutation lists, then require that the resulting 68-name model sequence matches the corresponding genomic sequence in all four authorities: `feature_contract.json.model_feature_names`, fitted preprocessor output names from `track_b_feature_names`, adapter `feature_names`, and the fitted coefficient/summary indexes.

The remaining 12 model names must equal the complement of the 68 explicit genomic names, remain outside every R8 feature row, and appear only as source-validation evidence. All raw and model names must be unique; expression and mutation model names must be disjoint. A missing, duplicate, reordered, additional, or colliding name blocks analysis.

## Coefficient extraction contract

R8 reads coefficients from the verified adapter's fitted `CoxPHFitter.params_` and model-reported fields from `CoxPHFitter.summary`, joined by exact model feature name. Positional-only joins are prohibited even though order is independently verified.

The framework-independent feature record is `PrognosticFeatureEffect` with this stable content:

- `rank`: one-based absolute-effect rank;
- `frozen_genomic_order`: one-based R6 genomic tie-break order;
- `raw_feature_name`;
- `model_feature_name`;
- `feature_type`: `expression` or `mutation_presence`;
- `beta`;
- `abs_beta`;
- `hazard_ratio`;
- `direction`;
- `direction_display`;
- `is_active`;
- model-reported penalized-Cox summary fields defined below.

Every one of the 68 mapped coefficients must appear exactly once. `beta`, `abs_beta`, and `hazard_ratio` must be finite. Boolean, missing, duplicate, or nonnumeric coefficient values block analysis.

The observed frozen model currently has 24 active and 44 effectively-zero genomic coefficients under the approved tolerance. Those counts are inspection evidence only: implementation derives them and never uses them as control constants.

## Coefficient tolerance and activity contract

The single numerical reporting constant is:

```text
COEF_EPS = 1e-6
```

The stable field name is `is_active`:

- `is_active=True` exactly when `abs(beta) > COEF_EPS`;
- `is_active=False` exactly when `abs(beta) <= COEF_EPS`.

This is an engineering threshold for reporting penalized floating-point coefficients. It is not a statistical-significance threshold, feature-selection claim, biological cutoff, or evidence that an inactive feature is unimportant outside this fitted model.

Direction uses the same threshold and freezes these machine-readable values and display text:

| Condition | `direction` | `direction_display` |
|---|---|---|
| `beta > COEF_EPS` | `associated_with_higher_modeled_hazard` | Associated with higher modeled hazard |
| `beta < -COEF_EPS` | `associated_with_lower_modeled_hazard` | Associated with lower modeled hazard |
| `abs(beta) <= COEF_EPS` | `effectively_zero_under_r8_threshold` | Effectively zero under the R8 numerical coefficient threshold |

The threshold boundary is inclusive for the effectively-zero class. `selected_by_lasso`, `significant`, `protective_gene`, and similar fields are prohibited.

## Ranking contract

The primary rank is deterministic:

1. descending `abs_beta`;
2. ascending `frozen_genomic_order` for exact ties.

Ranks are consecutive integers from 1 through 68. All features, including effectively-zero rows, remain in the full table. `is_active`, p-values, confidence bounds, feature type, and direction do not alter ranking. No canonical top-N artifact is created.

The human report contains the full 68-row ranking. Aggregate direction/activity counts are views of that table, not alternative rankings.

## Hazard-ratio contract

R8 derives `hazard_ratio = exp(beta)` with `math.exp` after finite-beta validation. Overflow, non-finite output, zero, or a negative result blocks analysis. The derived value must agree with lifelines' model-reported `exp(coef)` within `1e-12` relative and absolute tolerance.

No reciprocal hazard ratio, composite risk score, patient risk, or custom normalized importance is added. Beta, absolute beta, and exponentiated beta are sufficient.

## Penalized-Cox inference-statistics policy

The inspected frozen model exposes these finite fields for all 80 coefficients, and R8 preserves them for the 68 genomic rows:

- `standard_error` from `se(coef)`;
- `beta_ci_lower_95` and `beta_ci_upper_95`;
- `hazard_ratio_ci_lower_95` and `hazard_ratio_ci_upper_95`;
- `comparison_to` from `cmp to`;
- `z_statistic`;
- `p_value`;
- `negative_log2_p_value` from `-log2(p)`.

They are labeled collectively as `model_reported_penalized_cox_summary`. R8 validates that each preserved value is finite and that confidence-bound ordering is coherent. If a future verified serialization of this exact model cannot expose one of these fields, analysis blocks rather than inventing or silently dropping a contract field.

These values are descriptive output from one fitted penalized Cox model. P-values and intervals do not drive rank, activity, filtering, direction, or report emphasis. R8 does not apply p-value thresholds, multiplicity procedures, significance stars, or terms such as statistically significant, validated, discovered, or confirmed.

## Expression interpretation boundary

R6 applied a `StandardScaler` fitted on training data to the 50 expression inputs. Therefore, an expression beta is the modeled log-hazard association per one training-standardized expression unit, conditional on the other Track B predictors.

Absolute expression coefficients can be ranked on the fitted model scale. They are not effects per raw expression unit, causal gene effects, or externally validated biological effect sizes.

## Mutation interpretation boundary

R6 transformed each selected mutation annotation into a binary presence feature using the existing R4D semantics. R8 does not read or reparse raw annotations. A mutation beta is the modeled log-hazard association for mutation presence versus absence, conditional on the other Track B predictors.

It is not variant-specific, causal, a driver classification, or proof of a disease mechanism. Because expression inputs are standardized continuous values while mutation inputs are unscaled binary indicators, cross-type `abs_beta` ranking is explicitly a model-scale association ranking rather than biological unit equivalence.

## Artifact bundle

The canonical non-overwriting bundle is:

`artifacts/analysis/r8-prognostic-features-v1/`

It contains exactly:

- `feature_effects.csv`: the canonical full 68-row table in fixed column order;
- `metadata.json`: source lineage, contracts, runtime, and reproducibility policy;
- `summary.json`: aggregate feature/activity/direction counts and analysis status;
- `report.md`: scientific boundary, method, full 68-row ranking, aggregate summaries, and limitations;
- `audit.json`: the independent 30-check result;
- `checksums.sha256`: SHA-256 for every other file, sorted by filename.

`feature_effects.json` and separate higher/lower-hazard CSVs are omitted because they duplicate the canonical CSV without adding a distinct contract. The bundle contains no patient identifiers, patient rows, durations, event values, predictions, probabilities, row-level risk scores, source data, model pickle, or preprocessor pickle.

The exact CSV column order is `rank`, `frozen_genomic_order`, `raw_feature_name`, `model_feature_name`, `feature_type`, `beta`, `abs_beta`, `hazard_ratio`, `direction`, `direction_display`, `is_active`, `standard_error`, `beta_ci_lower_95`, `beta_ci_upper_95`, `hazard_ratio_ci_lower_95`, `hazard_ratio_ci_upper_95`, `comparison_to`, `z_statistic`, `p_value`, `negative_log2_p_value`. Floats use round-trip-safe `.17g` text. JSON is UTF-8, sorted-key, indented, newline-terminated, and rejects NaN/Infinity. Markdown and CSV use UTF-8 with LF line endings. The report's feature values are rendered from the same typed records as the CSV rather than reparsed or recomputed independently.

## Metadata and lineage

`metadata.json` records at minimum:

- schema version and analysis ID `r8-prognostic-features-v1`;
- source track `R6 Track B`, source experiment `r6-track-b-v1`, and source bundle path;
- R6 frozen implementation commit, R6 artifact-generation commit, and R8 generation commit;
- source model, preprocessor, feature-contract, metadata, and checksum-manifest hashes;
- inherited prepared-data and manifest paths/hashes;
- R6 model class, baseline method, penalizer, l1 ratio, and alpha;
- total encoded R6 feature count `80`;
- excluded clinical encoded count `12`;
- analyzed total `68`, expression `50`, mutation presence `18`, and clinical `0`;
- exact ordered raw-to-model genomic mapping;
- `COEF_EPS`, `is_active` rule, direction rules, and ranking rule;
- inferential-field label and non-selection policy;
- float/JSON/CSV serialization policy;
- Python, lifelines, pandas, NumPy, and project package versions;
- generation timestamp in UTC.

Source hashes come from newly verified bytes and must agree with the R6 checksum manifest and R6 metadata. They are not copied blindly.

## Trusted artifact loading

Pickle loading occurs only after path and checksum verification and only through `load_trusted_pickle(..., trusted=True)`. The loaded model must be a fitted repository `PenalizedCoxPHAdapter` containing a lifelines `CoxPHFitter`; the preprocessor must expose the validated 80-name order through `track_b_feature_names`.

Historical engineer pickles, arbitrary user paths, downloaded models, alternative R6 bundles, and objects that merely resemble the expected interface are prohibited. `cognivex_ml/scripts/generate_feature_importance.py` is reference-only. Its basic concepts of coefficient extraction, `exp(beta)`, and absolute-coefficient ordering are reusable; its prefix-based genomic discovery, unverified pickle loading, exact-zero Lasso flag, Track D naming, p-value significance stars, and causal/biological wording are explicitly rejected.

## Component boundaries and public interfaces

Future implementation follows current repository patterns with one new analysis package:

- `src/contracts/prognostic_features.py` defines framework-independent enums and immutable serializable feature, result, and audit contracts.
- `src/analysis/prognostic_features.py` owns explicit mapping validation, coefficient extraction, derived values, ranking, and report-safe summaries. It imports no training module.
- `src/artifacts/prognostic_features.py` verifies and loads the trusted R6 source, writes the non-overwriting R8 bundle, verifies checksums, and performs read-only semantic reproduction.
- `src/audit/prognostic_features.py` evaluates exactly the 30 frozen R8 checks.
- `scripts/analyze_prognostic_features.py` creates the canonical bundle once.
- `scripts/audit_prognostic_features.py` writes the independent audit and final checksums.
- `scripts/verify_prognostic_feature_artifacts.py` performs read-only checksum, lineage, table/report, and semantic-reproduction verification without writing or fitting.

Primary public interfaces are:

```python
verify_and_load_track_b_source(bundle: Path, repository_root: Path) -> VerifiedTrackBSource
build_genomic_feature_mapping(feature_contract: Mapping[str, object], model_feature_names: tuple[str, ...]) -> tuple[GenomicFeatureMapping, ...]
extract_prognostic_feature_effects(source: VerifiedTrackBSource, mapping: tuple[GenomicFeatureMapping, ...], coef_eps: float = COEF_EPS) -> PrognosticFeatureAnalysisResult
write_prognostic_feature_bundle(result: PrognosticFeatureAnalysisResult, source: VerifiedTrackBSource, output_root: Path) -> Path
verify_prognostic_feature_bundle(bundle: Path, r6_bundle: Path, repository_root: Path) -> PrognosticFeatureBundleVerification
audit_prognostic_feature_bundle(bundle: Path, r6_bundle: Path, repository_root: Path, full_test_suite_summary: str) -> PrognosticFeatureAuditReport
```

`VerifiedTrackBSource` is an internal trusted-boundary value containing verified objects and immutable lineage evidence. Contracts persisted outside that boundary contain no pickle or patient data.

## Audit design

The independent audit contains exactly 30 numbered PASS/FAIL checks:

1. Canonical R6 bundle identity is correct.
2. R6 model checksum and identity are unchanged.
3. R6 preprocessor and feature contract are unchanged.
4. R5 source and artifacts are unchanged.
5. R7 source and artifacts are unchanged.
6. R8 performs no model or preprocessing fitting.
7. Exactly 68 genomic predictors are analyzed.
8. Exactly 50 expression predictors are analyzed.
9. Exactly 18 mutation-presence predictors are analyzed.
10. Zero clinical predictors enter the genomic ranking.
11. Raw-to-model genomic mapping matches all frozen R6 orders.
12. Every genomic coefficient exists exactly once.
13. Every beta is finite.
14. Every `abs_beta` equals `abs(beta)`.
15. Every hazard ratio equals `exp(beta)` within the frozen tolerance.
16. Every hazard ratio is finite and positive.
17. `COEF_EPS` and `is_active` are applied exactly.
18. Direction labels and display text match beta and tolerance.
19. Ranking is descending by absolute beta.
20. Exact ties follow frozen genomic order.
21. Effectively-zero features remain present and are labeled consistently.
22. Model-reported inferential values are not used for ranking, activity, or filtering.
23. Historical engineer pickles were not loaded.
24. No patient-level data is persisted.
25. Report, summary, and feature table agree.
26. Metadata lineage points to the exact frozen R6 source.
27. Final bundle checksums verify.
28. Artifact generation is reproducible and read-only relative to R6.
29. The complete test suite passes.
30. R9 was not started.

Any failed check makes audit status `BLOCKED`; only 30 passing checks yield `PASS`. Audit evidence is concrete and machine-readable. Check 6 combines import-boundary/AST assertions with tests that replace fitting methods and training entrypoints with fail-fast sentinels. Check 28 recomputes analytical content in memory and compares it with persisted deterministic content while verifying all R6 bytes are unchanged before and after.

## Testing strategy

Future implementation uses controlled synthetic records for numerical edge cases and the canonical bundle for integration evidence.

Feature mapping tests prove exact 50/18/68 counts, zero clinical rows, unchanged selected order, exact mutation raw-to-`_present` mapping, four-authority order agreement, uniqueness, and fail-loud behavior for missing, duplicate, reordered, colliding, or extra names.

Coefficient tests cover positive beta, negative beta, exact zero, tiny positive and negative values below the threshold, both exact threshold boundaries, values immediately above each boundary, non-finite rejection, safe exponentiation, and equality with model-reported hazard ratio. They prove the frozen direction labels/text and `is_active` semantics.

Ranking tests prove descending `abs_beta`, frozen-order ties, consecutive ranks, retention of all 68 rows, and that activity, p-value, interval, direction, and feature type do not filter or reorder rows.

Statistical-language tests prove summary fields are labeled as model-reported penalized-Cox values, do not drive ranking, and never produce significance stars or unsupported words such as causal, driver, protective gene, significant biomarker, validated, or confirmed. Interpretation tests persist the expression-standardization and mutation-presence notes.

Trust tests prove checksum verification occurs before pickle loading, untrusted loading is denied, wrong paths/types/configurations are rejected, engineer pickle paths are rejected, and no fit or training entrypoint is called. R6 source hashes must be identical before and after analysis.

Artifact tests prove non-overwriting behavior, exact file set, no patient fields, deterministic column/key order, finite-only serialization, checksum verification, report/table/summary agreement, fixed-time byte reproduction, semantic reproduction with real runtime metadata, and audit failure propagation. A single failed audit check must produce `BLOCKED`.

Final verification runs focused R8 tests, the full pytest suite, compileall, `pip check`, `git diff --check`, read-only bundle verification, source-hash comparison, and repository-status inspection.

## Reproducibility

Analytical content is a pure function of the verified R6 model, verified preprocessor/feature contract, `COEF_EPS`, and this schema version. No random operation, patient-row order, current dataset read, or wall-clock value affects feature mapping, values, directions, or ranks.

`feature_effects.csv`, `summary.json`, and the analytical portion of `report.md` must be byte-identical when generated from identical source bytes and code. `generated_at_utc` and generation Git commit are declared provenance fields and are excluded from the semantic-content comparison; tests inject fixed values to verify complete byte determinism. `checksums.sha256` proves integrity of the particular emitted bundle.

Reproduction is read-only: verification recomputes the analysis in memory from the same trusted R6 artifacts and never overwrites the canonical R8 bundle or refreshes its checksums. The frozen feature order supplies all tie resolution.

## Scientific and interpretation limitations

R8 reports model-associated prognostic features from one penalized Cox model fitted on the locked internal METABRIC split. Its coefficients are conditional on the other 79 model features, the approved preprocessing, one predefined genomic panel, and one validation-selected regularization configuration.

R8 does not establish causal effects, validated biomarkers, clinical actionability, independent biological mechanisms, external validity, or statistical discovery in a confirmatory sense. The mixed R6 validation/test comparison, absent external validation, model penalization, correlated predictors, and differing expression/mutation scales all limit interpretation.

Permitted language is `model-associated prognostic feature`, `associated with higher modeled hazard`, `associated with lower modeled hazard`, and `effectively zero under the R8 numerical coefficient threshold`. Unsupported claims are prohibited even when a model-reported p-value is small.

## Explicit out of scope

R8 does not include:

- any new survival-model training, fitting, refitting, tuning, or selection;
- R6 retraining or hyperparameter changes;
- a Track D survival model or use of the 173-feature mutation selector/burden pipeline;
- R7 classifier feature importance;
- permutation importance or SHAP;
- pathway enrichment, gene ontology, literature validation, or external cohort validation;
- clinical recommendations or patient-level inference;
- risk-score persistence or analysis orchestration;
- Streamlit integration or deployment;
- R9 or any later increment.

## Design self-review

The specification was checked against the inspected R5–R7 repository state and frozen R6 objects.

- All contract and interface decisions are resolved.
- R8 never fits a model or preprocessor and always sources effects from frozen R6 Track B.
- Counts are consistently 80 total encoded, 68 analyzed genomic, 50 expression, 18 mutation presence, and 0 clinical ranked.
- The raw-to-model mapping is exact, collision-checked, and independent of dtype/prefix discovery.
- `COEF_EPS` has one definition; all 68 rows remain in the canonical table.
- Hazard-ratio mathematics, finite checks, penalized-summary labeling, and non-significance policy are explicit.
- Only checksum-verified trusted R6 pickles can be loaded; engineer pickles are prohibited.
- Ranking, tie-breaking, serialization, semantic reproduction, and lineage are deterministic.
- R5, R6, and R7 remain frozen; no Streamlit, inference, R7 explanation, new Cox model, or R9 work enters scope.
