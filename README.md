# Cognivex

Cognivex is a Python/Streamlit research prototype for **Breast Cancer Prognosis & Subtype Classification**. The central future comparison is clinical-only survival prognosis versus clinical-plus-genomic prognosis, with molecular subtype classification and gene-level model insight as separate analytical tasks.

## R5A status

R5A adds a clinical-only Cox proportional-hazards development baseline on top of the canonical R2–R4D METABRIC foundation. The repository includes:

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
- a persistent research/educational disclaimer.

The active application uses `data/metabric/prepared/METABRIC_prepared.csv` for cohort records. The immutable raw source and supplied metadata are retained for integrity and reproducibility checks. No patient-level rows are rendered.

The current canonical scan is `DATA_QUALITY_READY_WITH_WARNINGS`. Track A now drops Stage 1 and Negative ER-IHC/PR/HER2 as explicit reference categories, producing a full-rank 12-feature training matrix. The frozen R5A run converged without warnings and produced development C-index values of 0.671466 on training and 0.650696 on validation. The 286-patient test split was not transformed, predicted, or scored. These are development results, not clinical-performance claims.

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

See [R5A survival baseline](docs/survival_baseline.md), [architecture](docs/architecture.md), [contracts](docs/api_contracts.md), [data handoff](docs/data.md), [data quality](docs/data_quality.md), [preprocessing](docs/preprocessing.md), [Track D mutation preprocessing](docs/mutation_preprocessing.md), [active provenance resolution](docs/data_provenance_resolution.md), [setup](docs/setup.md), [testing](docs/testing.md), [limitations](docs/limitations.md), and the [problem-statement migration note](docs/migration.md).
