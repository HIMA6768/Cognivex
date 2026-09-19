# Implementation log

## 2026-09-19 — R6-P0 engineer import and compatibility audit

Imported the 30-file `cognivex_ml/` tree from `origin/anay/prediction_pipelines` commit `f4af52c` without merging the branch. Its nine pickle artifacts remain ignored, untrusted, and disconnected. Added a read-only compatibility module, direct CLI, focused tests, and deterministic JSON/Markdown artifacts. Source inspection is AST-only and does not execute engineer entrypoints.

The active Cognivex authority remains the 1,904-row, 693-column prepared METABRIC dataset and 1,332/286/286 locked manifest. The active prepared survival column is already 1=deceased/event and must not pass through the engineer loaders that invert 1=living source status. The engineer contract matches 50/50 expression and 18/18 mutation names exactly. Expression is fully consumable. For all 18 annotation-string mutation fields, review approved the existing R4D mutation contract: trimmed numeric zero maps to absence, valid non-zero annotations map to presence, and missing/malformed values fail clearly. The source CSV remains unchanged; no fitting, prediction, test evaluation, R7, or R8 work occurred.

## 2026-09-18 — R5/R5A clinical-only Cox PH baseline

Added framework-independent survival experiment contracts, deterministic matrix diagnostics, Harrell C-index evaluation, a strict lifelines 0.30.3 adapter, train/validation orchestration, checksummed artifact persistence, and a direct training CLI. The initial full-category 16-column Track A matrix had rank 13 and the unpenalized fit stopped on a singular matrix without a fallback.

R5A changed only Track A categorical encoding to fixed references: Stage 1 and Negative ER-IHC/PR/HER2. Tracks B/C/D remained unchanged. The canonical 1,332-row training matrix now has 12 columns, rank 12, condition number 966.312676, and no zero-variance, duplicate, or exact-dependency finding. The approved unpenalized model converged without warnings. Training C-index is 0.671466 and validation C-index is 0.650696 on 285 rows. PH diagnostics flagged age, Stage 2, Stage 3, ER-positive, and PR-positive. Stage 4 remained finite with HR 1.661750 and 95% CI 0.709586–3.891581. The 286-row test split was not transformed, predicted, or scored.

## 2026-09-18 — R4D Track D mutation preprocessing

Added the `clinical_mutation_survival` / Track D contract, shared mutation parser, cloneable fit-local inclusive 5% selector, all-173-gene log1p burden transformer, survival-based eligibility, and a fresh clinical-plus-mutation pipeline. Track D standardizes age, imputed tumor size, positive-node count, and log1p burden while leaving one-hot, missing-indicator, and selected mutation-presence outputs unscaled; fitted metadata records both groups explicitly. Canonical verification reports 1,903 eligible rows (1,332/285/286), 27 retained genes, and 44 outputs for the current locked full-training fit. The 27/44 values are evidence only, not constants. Aggregate UI readiness now covers Tracks A–D; no model or metric was created.

## 2026-09-18 — R4D-P0 locked-training mutation profiling

Added read-only, deterministic mutation evidence profiling against the manifest-confirmed training split. The profile covers the 173 canonical mutation annotation fields only, confirms canonical `"0"` as the no-mutation representation, and writes aggregate per-gene prevalence, candidate frequency flags, burden statistics, JSON, and Markdown evidence to `results/`. The raw/prepared hashes remain unchanged, Track B retains zero mutation predictors, and no threshold, production mutation-burden feature, Track D preprocessor, model, or metric was introduced.

## 2026-09-18 — R4 post-integration Data / Cohort status cleanup

Preserved the canonical R3 result of `DATA_QUALITY_READY_WITH_WARNINGS` (0 errors, 3 warnings, 6 information findings) and updated its stale R4 decision prompts to describe implemented policies. The Data / Cohort page now separately derives `PREPROCESSING_READY` from the read-only R4 canonical verification report, showing aggregate Track A/B/C readiness without exposing patient-level records. No canonical artifact, R2/R3 rule, eligibility rule, model, or analysis behavior changed.

## 2026-09-18 — R4 Leak-safe preprocessing

Implemented framework-independent eligibility/metadata contracts and three fresh sklearn-compatible factories. Track A applies training-only tumor-size median and ER-IHC mode imputation, schema-ordered unknown-safe categorical encoding, exact original-value missing indicators, and no numeric scaling. Track B appends exactly 489 canonically ordered mRNA features with a training-fitted `StandardScaler`. Track C retains those canonical expression Z-scores unchanged; source subtype labels are normalized separately as y.

Canonical read-only verification reports Track A 1,903 eligible (1,332/285/286 by train/validation/test), Track B the same, and Track C 1,898 eligible (1,330/285/283), with six NC exclusions only from Track C. The zero-duration validation row is excluded only from survival tasks and remains Track C eligible. R4 confirms 20 tumor-size and 30 ER-IHC indicators, 16/505/489 transformed features, zero mutation predictors, zero forbidden predictors, unchanged fit state after holdout transforms, and unchanged raw/prepared hashes. No model or metric was created.

## 2026-09-17 — R3 Biomedical data quality validation

Implemented a framework-independent, deterministic R3 quality scanner that runs only after R2 structural validation returns `DATA_READY`. It reads the canonical prepared CSV and existing R2 schema, feature-group, subtype, mapping, and manifest artifacts without modifying any data. The scanner returns aggregate-only error/warning/information findings and engineering readiness status; its 1,200-month survival-duration sentinel is a documented non-clinical review heuristic.

The canonical scan is `DATA_QUALITY_READY_WITH_WARNINGS`: 0 errors, 3 warnings, and 6 information findings. It reports 1,904 records, 1,103 events, 801 censored records, one zero survival duration, 20 missing tumor-size values, 30 missing ER-IHC values, 505 accepted `Unknown` tumor-stage values, 489 mRNA and 173 mutation features, and no missing/non-numeric/infinite/zero-variance genomic features. Mutation columns are validated as annotation fields rather than forced through an invented numeric encoding. No imputation, scaling, encoding, filtering, rebalancing, split regeneration, modeling, prediction, metric, or clinical decision behavior was added.

## 2026-09-17 — R2 Canonical METABRIC data ingestion

Installed one checksum-verified, repository-owned corrected METABRIC handoff under `data/metabric/`: immutable raw source, canonical prepared data, schema, feature groups, summary, patient mapping, locked 70/15/15 manifest, original provenance/checksum artifacts, strategy, and preparation script. The raw CSV is 8.00 MiB and the prepared CSV is 7.86 MiB, so Git LFS was not introduced.

Implemented framework-independent aggregate-only validation of required artifacts, imported checksums, declared schema, unique identifiers, one-to-one patient/sample mapping, and manifest partitions. The Data / Cohort page caches only a typed aggregate result, renders no source rows, and identifies the preserved historical provenance separately from the verified Kaggle provenance resolution. Semantic preparation reproduction is tested without requiring byte-identical serialization. No preprocessing, model, prediction, evaluation, gene importance, or clinical decision behavior was added.

## 2026-09-17 — R1 Biomedical domain reset

Created `codex/r1-biomedical-domain-reset` and committed the unchanged P8 tree as `3cb90f7` before migration. Superseded P1–P8 plans, specifications, and domain documents were moved into `docs/legacy/auto-insurance/`.

The active application now presents a seven-page biomedical research shell, domain-neutral settings, pending-only analysis contracts, and a persistent healthcare safety disclaimer. Image processing, damage/localization adapters, and insurance policy modules were removed from the active tree together with their obsolete tests. No data ingestion or model behavior was added; the exact dataset schema and subtype taxonomy remain pending handoff.

## 2026-09-17 — P8 Policy-only routing decision engine

Implemented `evaluate_routing()` as a pure P5/P6/P7 contract consumer. Quality failure has highest precedence and preserves P5 remediation; unavailable classification routes to review; moderate/severe labels, missing or low scores, and configured signal conflicts accumulate ordered human-review reasons; only a qualifying minor case receives `FAST_TRACK_ELIGIBLE`.

`PolicySettings` owns environment-backed score thresholds and a deliberately narrow `scratch -> structural` conflict pair. Localization remains supplementary: missing, unavailable, or zero detections do not block classifier policy. P7 mock inputs are supported only as deterministic development fixtures. Thresholds remain **PROVISIONAL DEVELOPMENT POLICY**, with real calibration, outcome evaluation, orchestration, and result UI deferred.

## 2026-09-17 — P5 blur scene-coverage correction

Replaced P5's median-tile sharpness criterion with a configured usable-sharp-tile ratio. A P5 blur pass now requires global Laplacian variance to clear its existing floor and at least 75% of 4×4 spatial tiles to clear the configured local sharpness floor. This prevents sharp text, line overlays, and footer/banner graphics from replacing scene-level sharpness, without detecting or removing any watermark. The ratio is a **PROVISIONAL ENGINEERING DEFAULT** selected only with controlled fixtures; it requires representative vehicle-photo calibration.

## 2026-09-17 — Pre-P8 contract and quality-gate corrections

Corrected the P6 routing schema to require an ordered, non-empty tuple of `RoutingReason` values under `RoutingDecision.reasons`. This is only a contract correction: the project still has no routing policy, status selection, or P8 behavior.

Hardened P5 without altering P6/P7 interfaces or mock adapters. Blur now requires both a global Laplacian variance and the median variance of a fixed 4×4 spatial grid, preventing a small sharp text/graphic region from dominating a broadly blurred scene. Darkness and brightness now combine mean and median luminance with configurable dark/bright-pixel tail ratios, reducing false passes from isolated headlights, reflections, or dark details. These controls remain **PROVISIONAL ENGINEERING DEFAULTS**, selected only with controlled fixtures and requiring the documented vehicle-photo calibration process.

## 2026-09-17 — P7 Deterministic mock adapters

Implemented framework-free classifier/localizer protocols and deterministic mock adapters that consume the minimal P4 image surface. The default behavior derives labels and zero/one/two detection selection from SHA-256 of the P4 image digest; explicit development scenarios cover normal minor/scratch, severe, low score, unavailable classifier, and unavailable/no/one/multiple/disabled localization paths. All boxes are converted from fixed fractional regions into valid coordinates within the actual normalized image dimensions.

P6 contracts now expose mock provenance, illustrative scores, and availability states without adding calibration or policy. Every mock result serializes `mock: true` and must be presented as awaiting the trained-model handoff. P7 parses mock/localization switches but does not initialize a model runtime or wire mock results into Streamlit. No ONNX, PyTorch, YOLO, NMS, routing, or decision behavior was added.

## 2026-09-17 — P6 Shared schemas and integration contracts

Implemented a dependency-free `src.contracts.assessment` schema module with frozen, slot-backed, JSON-compatible contracts for validation, quality, classification, localization, routing, and aggregate assessment results. P4 now offers a lossless adapter into the canonical validation contract; P5 uses canonical quality report types while preserving its deterministic behavior.

The contract vocabulary preserves all severity and damage labels, exposes mock/live model metadata with versions and experiment/preprocessing fields optional pending the AI handoff, and declares routing statuses without a routing policy. Added a representative vehicle-photo quality-threshold calibration protocol. P5 values remain **PROVISIONAL ENGINEERING DEFAULTS**. No inference, YOLO, routing logic, model metadata values, or result UI was added.

## 2026-09-17 — P5 Image quality gate

Implemented a pure P5 `evaluate_quality()` boundary that consumes P4 `ValidatedImage` previews only. It reports all deterministic blur, darkness, and brightness checks with stable uppercase codes, configured thresholds, technical measurements, safe remediation messages, and elapsed milliseconds. P5 composites transparency over white, bounds grayscale processing to a 512-pixel side, and uses four-neighbor Laplacian variance plus mean luminance.

The Assessment page retains P3/P4 session behavior and the P4 preview. It displays actionable quality failures, clears stale analysis intent, and disables Analyze Damage until P5 passes. The defaults are provisional engineering settings checked only with controlled fixtures; they have not been calibrated against representative vehicle photographs. No model, YOLO, resubmission route, routing outcome, or decision policy was added. Pending AI model handoff.

## 2026-09-17 — P4 Image validation

Implemented typed, pure structural validation for P3 uploads. The validator rejects unsupported, empty, oversized, malformed, extension/content-mismatched, animated, undersized, and excessively large images with stable uppercase codes and user-safe messages. It applies configured minimum/maximum width, height, and pixel limits, converts decompression-bomb warnings into safe failures, reduces filenames to display-only basenames, applies EXIF orientation to preview data, and normalizes opaque/grayscale images to RGB and alpha-bearing images to RGBA.

Session-state replacement and reset behavior remains unchanged. The Assessment page displays the normalized preview only after structural success and never emits a traceback for validation failures. P4 deliberately adds no blur, brightness, darkness, photographic-quality scoring, resubmission decision, inference, YOLO, routing, or decision behavior. Pending AI model handoff.

## 2026-09-17 — P3 Assessment upload UI

Implemented a polished Streamlit Assessment upload workflow for one JPG/JPEG, PNG, or WEBP image. The flow reads the operational `COGNIVEX_MAX_UPLOAD_MB` setting (10 MB by default), checks basic filename/type/byte-size/decode safety through a pure module, and holds validated bytes only in the current Streamlit session. Users receive an empty-state prompt, concrete photo tips, an invalid-file explanation, a structured preview, an Analyze Damage placeholder, and an Upload another image reset action.

Added configuration, pure upload-contract, and AppTest coverage for valid/invalid uploads, session persistence, analysis-placeholder behavior, and reset behavior. No image-quality gate, AI model, mock prediction, YOLO localization, decision engine, routing behavior, persistence, or external-service integration was added. Pending AI model handoff.

## 2026-09-17 — P2 Streamlit shell and visual design system

Implemented the Streamlit entrypoint and reusable UI shell: typed navigation, theme tokens, sidebar product identity, prototype status, page headers, safe empty states, and a persistent decision-support disclaimer. Added the five required presentation-only destinations: Assessment, Model Comparison, Model Insights, Monitoring, and System / About.

The assessment orientation describes the planned six stages without accepting an image. Comparison, insights, and monitoring explicitly remain empty until future evaluation or integration work exists. System / About documents the planned assessment flow and model families under evaluation without claiming a selected or evaluated model.

Added UI and Streamlit AppTest coverage for page registration, navigation, content contracts, responsive/accessibility CSS, and thin-entrypoint configuration. P2 deliberately adds no upload, validation, inference, localization, routing, metrics, external-service integration, or production readiness. Pending AI model handoff.

## 2026-09-16 — P1 Tasks 1–2

Implemented and tested the Task 1 side-effect-free configuration boundary: `AppSettings`, `ThresholdSettings`, `ConfigurationError`, and canonical severity and damage-type labels. Added the P1 Python/Streamlit dependency declaration and regression coverage for defaults, overrides, optional model fields, and invalid configuration values.

Documented the actual pre-model repository state, planned Streamlit-to-result flow, configuration exports, setup commands, limitations, and the preserved root `env.example` conflict. No application UI, model artifacts, credentials, model metrics, preprocessing contract, or production thresholds were introduced. Pending AI model handoff.
