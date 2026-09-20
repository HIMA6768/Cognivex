# Cognivex

Cognivex is a Python/Streamlit research prototype for **Breast Cancer Prognosis & Subtype Classification**. The central future comparison is clinical-only survival prognosis versus clinical-plus-genomic prognosis, with molecular subtype classification and gene-level model insight as separate analytical tasks.

## R9 status

R9 adds a framework-independent, trusted-local analysis service over the frozen R5, R6, R7, and R8 artifacts. It verifies text contracts and checksums before trusted pickle deserialization, initializes each track independently, and exposes only in-memory R5/R6 log-relative-hazard scores and the R7 subtype/probability output. Requests, feature values, patient identifiers, predictions, and probabilities are never persisted. This is research software, not a clinical decision system.

## R8 status

R8 adds a read-only prognostic genomic feature analysis of the frozen R6 Track B penalized Cox model. It excludes all 12 encoded clinical outputs and retains the complete ordered set of 50 expression plus 18 mutation-presence coefficients. Activity uses the frozen numerical rule `abs(beta) > 1e-6`; ranking uses descending absolute beta followed by frozen genomic order.

The current frozen evidence has 24 active and 44 effectively-zero coefficients. All 68 remain in the canonical table. These are model-associated coefficients from one internally evaluated penalized model—not causal effects, validated biomarkers, or clinical recommendations. R8 performs no fitting and persists no patient-level data.

The aggregate bundle is under `artifacts/analysis/r8-prognostic-features-v1/`, with a read-only verifier and independent 30-check audit. See [R8 analysis details](docs/prognostic_feature_analysis.md).

## R7 status

R7 adds a six-class molecular subtype classifier using exactly 50 selected expression features and 18 R4D-derived mutation-presence features, with zero clinical predictors. Track C eligibility is 1,330 train, 285 validation, and 283 test; NC exclusions are 2/1/3 and apply only to Track C.

Four frozen candidates were selected by validation Macro-F1 only. Random Forest won at 0.771384 validation Macro-F1. Its one-time final test evaluation produced Macro-F1 0.734176, weighted F1 0.748642, accuracy 0.749117, and balanced accuracy 0.719373. These are locked internal-split research results, not clinical validation or biological evidence. The test set did not influence selection.

The ignored trusted-local pipeline and committed aggregate evidence live under `artifacts/models/track_c/r7-track-c-v1/`; a read-only reload verifier and independent 28-check audit reproduce the frozen result.

## R6 survival foundation

R6 adds a penalized clinical-plus-genomic Cox proportional-hazards comparison on top of the frozen R5A clinical baseline and canonical R2–R4D METABRIC foundation. The repository includes:

- seven research-oriented navigation destinations;
- a responsive, accessible visual system;
- domain-neutral environment configuration;
- framework-independent pending-result contracts;
- SHA-256, schema, mapping, and locked-split validation;
- aggregate-only cohort/session-state integration; and
- deterministic error/warning/information quality findings, cached with the validated cohort;
- fresh sklearn-compatible preprocessors for clinical survival, clinical-plus-mRNA survival, subtype classification, and clinical-plus-mutation survival; and
- fit-local binary mutation selection at an inclusive 5% prevalence threshold plus all-173-gene log1p mutation burden; and
- a train-only, unpenalized Track A `CoxPHFitter` with fixed reference-category encoding, validation-only development evaluation, PH diagnostics, and versioned local artifacts; and
- a Track B pipeline with the same seven raw clinical predictors, exactly 50 selected expression predictors, exactly 18 R4D-derived mutation-presence predictors, validation-only regularization selection, and versioned local artifacts; and
- a persistent research/educational disclaimer.

The active application uses `data/metabric/prepared/METABRIC_prepared.csv` for cohort records. The immutable raw source and supplied metadata are retained for integrity and reproducibility checks. No patient-level rows are rendered.

The current canonical scan is `DATA_QUALITY_READY_WITH_WARNINGS`. Track A produces 12 reference-coded model features. Track B produces 80 model features from the frozen seven-field clinical contract plus the explicit 68-field genomic contract. All six predefined penalized Cox candidates converged; validation selected `penalizer=0.05`, `l1_ratio=0.5`. Track B C-index was 0.685775 on training, 0.644544 on validation, and 0.640915 on the one-time frozen-winner test evaluation. Relative to frozen Track A, the delta was -0.006152 on validation and +0.015932 on test. These are internal development results, not clinical-performance claims or evidence of generalizable genomic benefit.

## R6 provenance

The AI-engineer `cognivex_ml/` tree remains disconnected reference material. The active model reads only `data/metabric/prepared/METABRIC_prepared.csv` with the locked 1,332/286/286 manifest. The 18 annotation-string mutation fields are converted through the existing R4D contract without modifying the source CSV: trimmed numeric zero is absence, valid non-zero annotation is presence, and missing/malformed values fail clearly. Historical engineer pickles are not loaded.

## Run locally

Requires Python 3.11 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pip install -e ".[dev]"
streamlit run app.py
```

Run tests with:

```powershell
python -m pytest -q
```

## Safety boundary

This is a research and educational prototype. It is not a diagnostic medical device, treatment recommendation system, validated clinical prognosis system, or substitute for qualified oncology care. Do not use it for patient care.

See the generated [R8 report](artifacts/analysis/r8-prognostic-features-v1/report.md), [R7 report](artifacts/models/track_c/r7-track-c-v1/report.md), [R6 report](artifacts/models/track_b/r6-track-b-v1/report.md), [R6-P0 compatibility audit](docs/r6_p0_engineer_compatibility.md), [R5A survival baseline](docs/survival_baseline.md), [architecture](docs/architecture.md), [model training](docs/model_training.md), [model evaluation](docs/model_evaluation.md), [testing](docs/testing.md), and [limitations](docs/limitations.md).
