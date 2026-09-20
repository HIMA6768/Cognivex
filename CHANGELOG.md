# Changelog

## 2026-09-20 — R10-B0 validated Cox survival estimates

- Extended the typed Track A/B prognosis output with finite, bounded, monotonic 1-, 3-, and 5-year model-estimated survival probabilities.
- Used only each frozen Cox fitter's public `predict_survival_function` at 12, 36, and 60 months, including Lifelines-compatible off-index interpolation and no-extrapolation checks.
- Preserved the existing log partial-hazard output and avoided any artifact, model, training, or Streamlit visual redesign change.

## 2026-09-20 — R10-A functional Streamlit integration

- Connected the basic Streamlit Survival Analysis, Subtype Classification, and Gene Insights pages to the frozen R9 public service through a repository-relative cached accessor.
- Added typed readiness, safe error, intended output, and aggregate-only R8 rendering. No model contract, artifact, inference behavior, persistence, visual redesign, R11, or R12 work was added.

## 2026-09-20 — R9 trusted analysis orchestration

- Added framework-independent result contracts, checksum-gated artifact registry, transform-only R5/R6/R7 adapters, independent per-track readiness, and a read-only R8 aggregate view.
- Added an R9 audit lifecycle with provisional bootstrap evidence and final-only verification. No model fitting, refitting, tuning, Streamlit integration, patient-level persistence, or R10 presentation work was added.

## 2026-09-19 — R8 frozen-model prognostic genomic feature analysis

- Added checksum-gated, read-only coefficient analysis of the frozen R6 Track B model with no fitting, tuning, model selection, patient-row access, or historical engineer pickle loading.
- Mapped and retained exactly 50 expression plus 18 mutation-presence coefficients while excluding all 12 encoded clinical outputs.
- Frozen `COEF_EPS=1e-6`, strict activity/direction rules, and descending absolute-beta ranking with frozen-order tie resolution. Current evidence is 24 active and 44 effectively-zero coefficients; all 68 remain in the table.
- Added a deterministic aggregate-only artifact bundle, read-only semantic verifier, final-checksum coverage, and independent 30-check audit. No R9, inference, Streamlit, Track D model fitting, or deployment work was added.

## 2026-09-19 — R7 Track C molecular subtype classification

- Added the exact genomic-only Track C contract: 50 expression features, 18 R4D-derived binary mutation-presence features, 68 raw/model predictors, and zero clinical predictors.
- Applied Track-C-only target eligibility in canonical manifest order: 1,330 train, 285 validation, and 283 test, with NC exclusions of 2/1/3.
- Evaluated Logistic Regression, Random Forest, Gradient Boosting, and RBF SVM on validation only. Random Forest won by validation Macro-F1 (0.771384); only that frozen winner received test evaluation.
- Recorded final test Macro-F1 0.734176, weighted F1 0.748642, accuracy 0.749117, and balanced accuracy 0.719373.
- Added non-overwriting artifacts, trusted-local ignored pipeline persistence, deterministic prediction/probability digests, read-only reload verification, and an independent 28-check audit. No R8, biological interpretation, inference service, Streamlit integration, or deployment work was added.

## 2026-09-19 — R6 Track B clinical + genomic survival model

- Added the exact Track B contract: seven frozen R5 clinical predictors, 50 explicit selected expression predictors, and 18 selected mutation-presence predictors, yielding 75 raw and 80 encoded model features.
- Reused frozen R5 clinical preprocessing, train-fitted expression scaling, and existing R4D mutation parsing without rewriting canonical source annotations.
- Evaluated six predefined penalized Cox candidates on validation only and selected `penalizer=0.05`, `l1_ratio=0.5`; only that frozen winner received one test evaluation.
- Recorded Track B C-index values of 0.685775 train, 0.644544 validation, and 0.640915 test. Against frozen Track A, deltas were -0.006152 validation and +0.015932 test.
- Added versioned aggregate artifacts, trusted-local pickle persistence, exact reload verification, and a separate 25-check audit. R7 and R8 remain unstarted.

## 2026-09-19 — R6-P0 engineer import and genomic compatibility audit

- Imported `cognivex_ml/` from engineer commit `f4af52c` as disconnected reference material without merging its branch, split, data loaders, models, or metrics into the active runtime.
- Added a read-only, AST-based compatibility utility and deterministic JSON/Markdown audit artifacts. No engineer entrypoint is imported or executed.
- Confirmed the authoritative dataset remains the 1,904-patient, 693-column prepared METABRIC file with locked 1,332/286/286 splits and active `overall_survival` event coding of 1=deceased/event.
- Confirmed exact-name availability of 50/50 selected expression and 18/18 selected mutation features. All expression fields are numeric, finite, complete, and non-constant; all 18 mutation fields are annotation strings.
- Recorded approval to derive binary mutation presence through the existing R4D annotation contract without rewriting the prepared CSV. No model was trained, and R7/R8 were not started.

## 2026-09-18 — R5A Track A reference-category Cox PH baseline

- Replaced Track-A-only full dummy encoding with fixed references: Stage 1 and Negative ER-IHC, PR, and HER2. Tracks B, C, and D retain their prior preprocessing contracts.
- Added full-rank and condition-number gates, serializable category-versus-reference metadata, the approved unpenalized lifelines Cox PH adapter, Harrell C-index evaluation, PH diagnostics, and trusted local artifact persistence.
- The canonical 1,332-row training matrix changed from the historical 16-feature/rank-13 failure to 12 features at rank 12 with condition number 966.312676. The model converged without warnings.
- Recorded development C-index 0.671466 on training and 0.650696 on validation. The 286-row test partition was not transformed, predicted, or scored.
- Retained Stage 4 with finite but imprecise evidence (HR 1.661750; 95% CI 0.709586–3.891581). PH diagnostics flagged age, Stage 2, Stage 3, ER-positive, and PR-positive; no automatic remedy was applied.

## 2026-09-18 — R4D Track D mutation preprocessing

- Added the fresh `clinical_mutation_survival` Track D preprocessor with shared binary annotation semantics, an inclusive fit-local `>= 0.05` mutation selector, and all-173-gene `mutation_burden_log1p`.
- Added Track-D-specific train-fitted scaling for continuous clinical variables and burden while leaving clinical one-hot/missing indicators and mutation-presence indicators unscaled; typed metadata explicitly partitions those final groups.
- Added survival-based Track D eligibility, canonical verification, aggregate readiness UI, and regression coverage proving Track B remains mutation-free and Tracks A–C remain unchanged.
- The current locked full-training fit retains 27 genes and emits 44 features as canonical evidence only. No gene list/count is hardcoded, and no model, C-index, tuning, or patient prediction was introduced.

## 2026-09-18 — R4D-P0 locked-training mutation profiling

- Added deterministic, aggregate-only train-split profiling for the 173 canonical mutation annotation fields, including per-gene prevalence, candidate 1/2/5/10% flags, and mutation-burden evidence artifacts.
- Added patient-ID manifest joining, canonical annotation checks, train-only isolation, reconciliation, deterministic-output, immutable-artifact, and Track B zero-mutation regression coverage.
- No mutation threshold was selected; no Track D preprocessor, production burden feature, model, metric, or clinical behavior was introduced.

## 2026-09-18 — R4 post-integration Data / Cohort status cleanup

- Preserved `DATA_QUALITY_READY_WITH_WARNINGS` and its canonical 0-error, 3-warning, 6-information result while updating stale R4 decision prompts to describe implemented handling policies.
- Added a separately derived `PREPROCESSING_READY` Data / Cohort section backed by R4 canonical verification, with aggregate Track A/B/C readiness and no patient-level data.
- No canonical data, checksum behavior, R3 severity, locked manifest, eligibility rule, model, or clinical-decision behavior changed.

## 2026-09-18 — R4 Leak-safe preprocessing

- Added separate fresh sklearn-compatible preprocessors for Track A clinical survival, Track B clinical-plus-489-mRNA survival, and Track C mRNA-only subtype classification.
- Added train-only tumor-size/ER-IHC imputation, exact original-value missing indicators, deterministic schema-ordered encoding, Track B mRNA scaling, and approved Track C no-additional-scaler behavior.
- Added independent task eligibility, separate subtype target normalization, locked-manifest alignment, stable exclusion reasons, immutable-artifact verification, and fail-loud target/ID/split/mutation/eligibility leakage guards.
- Canonical verification reports 1,903 Track A rows, 1,903 Track B rows, and 1,898 Track C rows eligible; no model, prediction, C-index, gene selection, mutation Track D, or clinical decision behavior was introduced.

## 2026-09-17 — R3 Biomedical data quality validation

- Added framework-independent, aggregate-only quality contracts and a deterministic R3 scan gated by R2 `DATA_READY`.
- Added read-only survival, clinical, mapping/split, genomic, subtype/NC-policy, and aggregate-distribution findings with stable error/warning/information severity and engineering readiness statuses.
- Added cached Data / Cohort quality rendering, synthetic invalid-data coverage, and the documented non-clinical 1,200-month duration-review sentinel.
- No cohort mutation, imputation, encoding, scaling, filtering, rebalancing, model, prediction, metric, or clinical-decision behavior was introduced.

## 2026-09-17 — R2 Canonical METABRIC data ingestion

- Added one repository-owned corrected METABRIC handoff package with immutable raw data, canonical prepared data, locked manifest, patient/sample mapping, schema metadata, original checksum manifest, historical provenance, preparation script, and strategy documentation.
- Added framework-independent checksum, schema, identifier, mapping, and locked split validation returning aggregate-only typed results and stable data-validation error codes.
- Added session-backed Data / Cohort rendering for validated aggregate counts, clinical schema names, confirmed handoff subtype taxonomy, NC policy, and separately documented verified Kaggle provenance.
- Added semantic preparation reproducibility coverage without requiring byte-identical cross-version CSV output. No preprocessing, fitting, prediction, metric, gene-importance, or clinical decision behavior was introduced.

## 2026-09-17 — R1 Biomedical domain reset

- Checkpointed the complete P8 auto-insurance prototype before migration and archived its domain documentation, specifications, and plans for traceability.
- Replaced the active product identity, seven-page navigation, configuration, contracts, and Streamlit pending states for Breast Cancer Prognosis & Subtype Classification.
- Removed active image validation/quality, damage adapters/contracts, localization, insurance routing, and their obsolete tests; retained the responsive theme, safe layout utilities, configuration patterns, and AppTest infrastructure.
- Added a persistent research/educational disclaimer. No dataset processing, scientific metric, subtype taxonomy, model artifact, prediction, gene ranking, or patient-specific output was introduced.

## 2026-09-17 — P8 Policy-only routing decision engine

- Added a pure, deterministic routing engine returning the frozen P6 `RoutingDecision` contract with explicit quality, availability, severity, score, conflict, and minor-eligibility precedence.
- Added centralized stable reason codes, ordered multi-reason support, P5 remediation preservation, supplementary localization handling, and one configured `scratch -> structural` conflict rule.
- Added environment-backed **PROVISIONAL DEVELOPMENT POLICY** score thresholds and comprehensive table-driven P8/P7 integration tests. No inference, UI result rendering, orchestration, persistence, approval/rejection, or cost estimation was added.

## 2026-09-17 — P5 blur scene-coverage correction

- Replaced P5's median-tile blur criterion with a configured usable-sharp-tile ratio, preserving the global Laplacian safeguard and all stable P5 interfaces.
- Added a controlled blurred-scene fixture with sharp center overlay edges and a sharp footer banner, plus configuration-tuning coverage. No exposure, adapters, contracts, routing, UI behavior, or P8 policy changed.

## 2026-09-17 — Pre-P8 contract and quality-gate corrections

- Migrated the P6 `RoutingDecision` contract from one `reason` to a required ordered `reasons` collection, preserving multiple future policy reasons without implementing a policy.
- Hardened P5's deterministic blur check with a median 4×4 tile-Laplacian criterion, so small sharp graphics cannot let a broadly blurred scene pass.
- Hardened darkness and overexposure checks with median luminance and configurable dark/bright-pixel ratios, so isolated highlights or shadows cannot dominate the global mean.
- Added controlled regression coverage for localized sharp patches on blur, night highlights, inverse overexposure, plural routing serialization, and new configuration values. All added thresholds remain **PROVISIONAL ENGINEERING DEFAULTS**.

## 2026-09-17 — P7 Deterministic mock adapters

- Added framework-independent classifier/localizer protocols and deterministic digest-driven mock adapters that return P6 contracts.
- Added explicit controlled scenarios for normal, severe, low-score, unavailable, and localization zero/one/multiple/disabled states; mock detection boxes are clamped within actual P4 image dimensions.
- Added serialized `mock: true` provenance, illustrative mock scores, availability states, and `InferenceSettings` flags without activating real inference.
- Added adapter determinism, protocol, geometry, scenario, P4 compatibility, and configuration coverage. No ONNX, PyTorch, YOLO, routing policy, or Streamlit mock-result display was added.

## 2026-09-17 — P6 Shared schemas and integration contracts

- Added framework-independent, frozen, JSON-compatible contracts for P4 validation, P5 quality, P7 classification/localization, P8 routing, and P9 assessment aggregation.
- Preserved frozen severity/damage labels; added contract-only routing statuses and provenance metadata with mock/live state while leaving AI-handoff fields optional.
- Added P4-to-contract adaptation and made P5 use the canonical quality-report types without changing quality behavior.
- Added schema, validation, serialization, P4/P5 compatibility, and partial-pipeline tests. No inference, YOLO, routing policy, or result UI was added.

## 2026-09-17 — P5 Image quality gate

- Added pure, typed, deterministic P5 reports with stable blur, darkness, and brightness reason codes plus user-safe remediation messages.
- Added P4-to-P5 separation, white-background alpha compositing, bounded grayscale Laplacian variance and mean-luminance measurements, all-check evaluation, elapsed-time reporting, and configuration-backed provisional thresholds.
- Updated the Assessment UI to retain a P4 preview, present actionable quality failures, clear stale analysis intent, and disable Analyze Damage until quality checks pass.
- Added controlled-fixture and Streamlit regression coverage. No model, routing, resubmission disposition, or decision policy was added.

## 2026-09-17 — P4 Image validation

- Added typed structural validation results with stable uppercase error codes and user-safe messages.
- Added actual image decode/format verification, configured minimum and maximum dimensions, pixel-count/decompression safeguards, still-image enforcement, safe Unicode display names, EXIF-orientation normalization, and RGB/RGBA preview normalization.
- Added validation coverage for malformed/truncated files, MIME and extension/content mismatches, geometry boundaries, animated WebP, grayscale, transparency, orientation, and preserved session state.
- Deferred blur, brightness/darkness, photographic quality scoring, resubmission decisions, AI inference, YOLO, routing, and decisions to later increments.

## 2026-09-17 — P3 Assessment upload flow

- Added a session-persistent, drag-and-drop vehicle-image uploader with JPG/JPEG, PNG, and WEBP support.
- Added configured max-size handling through `COGNIVEX_MAX_UPLOAD_MB` (10 MB default), basic type/decode validation, corrective invalid-file states, structured preview, Analyze Damage placeholder, and upload-another reset flow.
- Added pure upload/state contracts and Streamlit integration tests for valid, invalid, persistent, and reset behavior.
- No image-quality gate, inference, mock prediction, YOLO, localization, routing, or decision engine was added. Pending AI model handoff.

## 2026-09-17 — P2 Streamlit shell and visual system

- Added a Streamlit application entrypoint, responsive product shell, typed five-page navigation, and reusable layout components.
- Added restrained navy/slate/blue visual tokens, high-contrast prototype status, visible focus styles, mobile column stacking, and scoped empty states.
- Added presentation-only Assessment, Model Comparison, Model Insights, Monitoring, and System / About pages with no fabricated metrics or model output.
- Added app-shell and UI-foundation regression coverage plus P2 architecture, setup, design, and user-flow documentation.
- Upload, validation, inference, localization, routing, external services, and production readiness remain deferred. Pending AI model handoff.

## 2026-09-16 — P1 pre-model foundation

- Documented the current Python/Streamlit repository state and planned architecture.
- Added the Task 1 side-effect-free `src/config` settings and threshold contracts, canonical labels, Streamlit dependency declaration, and configuration tests.
- Added setup, limitations, and implementation-history documentation.
- No model, credentials, inference behavior, or UI was added.
