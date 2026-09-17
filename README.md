# Cognivex

Cognivex is a Python/Streamlit research prototype for **Breast Cancer Prognosis & Subtype Classification**. The central future comparison is clinical-only survival prognosis versus clinical-plus-genomic prognosis, with molecular subtype classification and gene-level model insight as separate analytical tasks.

## R3 status

R3 adds a read-only, framework-independent quality review on top of the canonical R2 METABRIC handoff. The application includes:

- seven research-oriented navigation destinations;
- a responsive, accessible visual system;
- domain-neutral environment configuration;
- framework-independent pending-result contracts;
- SHA-256, schema, mapping, and locked-split validation;
- aggregate-only cohort/session-state integration; and
- deterministic error/warning/information quality findings, cached with the validated cohort; and
- a persistent research/educational disclaimer.

The active application uses `data/metabric/prepared/METABRIC_prepared.csv` for cohort records. The immutable raw source and supplied metadata are retained for integrity and reproducibility checks. No patient-level rows are rendered.

The current canonical scan is `DATA_QUALITY_READY_WITH_WARNINGS`: it reports aggregate clinical missingness and one zero-duration survival record without changing data. R3 does **not** add preprocessing, survival or subtype models, predictions, metrics, gene ranking, or patient-specific output.

## Run locally

Requires Python 3.11 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pip install -e ".[dev,data-preparation]"
streamlit run app.py
```

Run tests with:

```powershell
python -m pytest -q
```

## Safety boundary

This is a research and educational prototype. It is not a diagnostic medical device, treatment recommendation system, validated clinical prognosis system, or substitute for qualified oncology care. Do not use it for patient care.

See [architecture](docs/architecture.md), [contracts](docs/api_contracts.md), [data handoff](docs/data.md), [data quality](docs/data_quality.md), [active provenance resolution](docs/data_provenance_resolution.md), [setup](docs/setup.md), [testing](docs/testing.md), [limitations](docs/limitations.md), and the [problem-statement migration note](docs/migration.md).
