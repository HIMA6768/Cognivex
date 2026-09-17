# Changelog

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
