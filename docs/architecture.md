# Architecture

## Current R10-A state

The R10-A Streamlit layer is intentionally thin. `src.ui.analysis_service.get_analysis_service()` caches repository-relative construction of R9's `AnalysisService`; pages submit typed `AnalysisRequest` values through `submit_track_request()` and render only typed R9 outcomes. UI modules do not import model adapters, preprocessors, artifact loaders, or pickle handling. Gene Insights calls the separate R9 aggregate getter and renders all 68 global R8 effects without a patient-specific input or attribution path.

## Current R9 state

`src.artifacts.inference_registry` is the R9 trust boundary: canonical repository-relative R5/R6/R7/R8 bundles have their textual contracts and checksum manifests verified before any trusted-local pickle is deserialized. `src.services.analysis.AnalysisService` initializes model tracks independently, so one unavailable bundle cannot block other verified tracks. Its adapters only call persisted `transform`, `predict_risk`, `predict`, and `predict_proba`; no R9 module fits, retrains, or persists patient-level payloads. R5/R6 return only log partial hazard scores; R7 returns a frozen six-class subtype and normalized six-class probability tuple; R8 remains aggregate-only.

## Current R8 state

`app.py` configures Streamlit and delegates to `src/ui/shell.py`. The shell applies the package-owned theme, renders typed navigation, dispatches focused page renderers, and displays the research-only disclaimer after every page.

`src/data/metabric.py` resolves repository-relative canonical paths, verifies imported checksums, validates the prepared schema, patient/sample mapping, and manifest, then returns aggregate-only frozen contracts from `src/contracts/analysis.py`. `src/data/metabric_quality.py` runs only after that result is `DATA_READY`; it scans canonical prepared data and R2 metadata read-only, then returns aggregate quality contracts. `src/ui/data_cohort_state.py` also caches the aggregate R4 canonical-preprocessing verification report, allowing the Data / Cohort page to present canonical data-quality warnings separately from `PREPROCESSING_READY`. The page never receives patient rows.

`src/preprocessing/` provides immutable metadata loading, patient-aligned task eligibility, explicit predictor selection, four fresh sklearn-compatible factories, and canonical aggregate verification. R4D adds a shared mutation parser, fit-local binary frequency selector, and all-gene burden transformer. Contracts in `src/contracts/preprocessing.py` remain serializable without Streamlit or sklearn values. Final predictors never expose IDs, targets, split fields, raw mutation annotations, or eligibility metadata.

`src/data/mutation_profile.py` remains the R4D-P0 evidence-only boundary. Its full-training 27-gene result verifies, but does not configure, the production selector. Track D fits selection independently on every training/fold-training input and may retain a different set in future CV.

`src/training/track_a.py` owns the R5A train/validation orchestration. It consumes only Track A eligible rows, fits the Track-A-only reference-coded preprocessor on the locked training split, rejects non-finite or rank-deficient matrices before model construction, fits the approved unpenalized lifelines adapter, and evaluates training plus validation. It retains test only as an aggregate count. `src/evaluation/survival.py` owns Harrell C-index direction and matrix diagnostics; `src/artifacts/survival.py` writes checksummed experiment evidence and trusted local pickle files.

`src/preprocessing/track_b.py` owns the explicit R6 75-field input contract and composite transformer: frozen R5 clinical preprocessing, a train-fitted scaler for 50 selected expression fields, and the existing R4D annotation classifier for 18 binary mutation-presence fields. `src/training/track_b.py` fits six predefined penalized Cox candidates on train, selects exclusively by validation C-index, and evaluates only the frozen winner on test. `src/artifacts/track_b.py` persists aggregate evidence plus trusted local preprocessing/model pickles; `src/audit/track_b.py` independently evaluates the 25 frozen R6 audit checks.

R7 is an independent classification path. `src/data/track_c.py` freezes the 50/18 genomic feature order, six-class target order, Track-C-only exclusions, and canonical manifest ordering. `src/preprocessing/track_c.py` reuses the R4D mutation transformer and scales expression only for Logistic Regression and RBF SVM. `src/training/track_c.py` exposes no test data to candidate selection, selects solely by validation Macro-F1, and evaluates only the frozen winner once. `src/artifacts/track_c.py` persists aggregate evidence plus one ignored trusted-local pipeline; `src/audit/track_c.py` evaluates 28 independent checks. No Track C module imports survival modeling.

R8 is an analysis-only branch from the frozen R6 artifact boundary. `src/artifacts/prognostic_features.py` verifies every source checksum before trusted local deserialization; `src/analysis/prognostic_features.py` maps 50 expression and 18 mutation-presence coefficients while excluding the 12 encoded clinical outputs. All 68 genomic rows are retained and ranked only by absolute beta plus frozen-order ties. The artifact verifier recomputes evidence in memory and the independent audit evaluates 30 checks without reading patient rows or fitting a model.

`cognivex_ml/` is an imported engineer-reference boundary, not an application package or active model source. `src/data/engineer_compatibility.py` reads its source text through the AST, compares the explicit handoff feature list to canonical Cognivex data, and emits aggregate audit evidence under `artifacts/r6_p0/`. It never imports engineer scripts, fits preprocessing, trains a model, rewrites data, or changes the locked manifest. R6-P0 records the approved future use of `src.preprocessing.mutations.classify_mutation_annotation` for the selected 18 mutation fields while preserving source annotations.

## Navigation

The active order is Overview, Data / Cohort, Survival Analysis, Subtype Classification, Gene Insights, Model Comparison, and Methodology / About.

## Planned increments

```text
R2 validated data ingestion
  -> R3 data quality review and engineering-readiness findings
  -> R4 leak-safe preprocessing (complete)
  -> R4D Track D mutation preprocessing (complete)
  -> R5/R5A clinical-only survival baseline (complete development gate)
  -> R6-P0 engineer compatibility audit (complete; mutation mapping approved)
  -> R6 clinical-plus-genomic prognosis (complete development gate)
  -> R7 molecular subtype classification (complete development gate)
  -> R8 frozen-R6 prognostic genomic feature analysis (complete)
  -> R9 analysis orchestration
  -> R10 results and visualization
```

R5A supplies the frozen clinical-only baseline. R6 supplies one validation-selected Track B survival model. R7 supplies one validation-selected Track C subtype classifier using genomic predictors only. R8 reports aggregate model-associated genomic coefficients from frozen R6 without fitting. None adds patient-facing model output. Track D fitting, biological interpretation, patient predictions, external validation, and deployment remain pending later approved increments.

## Reused infrastructure

- Streamlit entrypoint and renderer registry.
- Responsive theme, accessible focus treatment, and safe layout helpers.
- Frozen dataclass and injected-environment configuration patterns.
- Framework-independent serialization pattern.
- pytest and Streamlit AppTest infrastructure.

The superseded implementation is archived under `docs/legacy/auto-insurance/` and preserved in Git checkpoint `3cb90f7`.
