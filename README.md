# Cognivex

Cognivex is a Python/Streamlit research prototype for **Breast Cancer Prognosis & Subtype Classification**. The central future comparison is clinical-only survival prognosis versus clinical-plus-genomic prognosis, with molecular subtype classification and gene-level model insight as separate analytical tasks.

## R6 status

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

See the generated [R6 report](artifacts/models/track_b/r6-track-b-v1/report.md), [R6-P0 compatibility audit](docs/r6_p0_engineer_compatibility.md), [R5A survival baseline](docs/survival_baseline.md), [architecture](docs/architecture.md), [contracts](docs/api_contracts.md), [data handoff](docs/data.md), [data quality](docs/data_quality.md), [preprocessing](docs/preprocessing.md), [Track D mutation preprocessing](docs/mutation_preprocessing.md), [active provenance resolution](docs/data_provenance_resolution.md), [setup](docs/setup.md), [testing](docs/testing.md), [limitations](docs/limitations.md), and the [problem-statement migration note](docs/migration.md).
