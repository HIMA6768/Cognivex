# Cognivex

Cognivex is a Python/Streamlit research prototype for **Breast Cancer Prognosis & Subtype Classification**. The central future comparison is clinical-only survival prognosis versus clinical-plus-genomic prognosis, with molecular subtype classification and gene-level model insight as separate analytical tasks.

## R1 status

R1 provides a runnable biomedical application shell only. It includes:

- seven research-oriented navigation destinations;
- a responsive, accessible visual system;
- domain-neutral environment configuration;
- framework-independent pending-result contracts;
- explicit pending-data and pending-model states; and
- a persistent research/educational disclaimer.

R1 does **not** ingest datasets, infer schemas, fit survival or subtype models, calculate metrics, rank genes, or present patient-specific output. Molecular subtype labels remain unresolved until the selected dataset is inspected.

## Run locally

Requires Python 3.11 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pip install pytest
streamlit run app.py
```

Run tests with:

```powershell
pytest -q
```

## Safety boundary

This is a research and educational prototype. It is not a diagnostic medical device, treatment recommendation system, validated clinical prognosis system, or substitute for qualified oncology care. Do not use it for patient care.

See [architecture](docs/architecture.md), [contracts](docs/api_contracts.md), [data handoff](docs/data.md), [model integration](docs/model_integration.md), [setup](docs/setup.md), [testing](docs/testing.md), [limitations](docs/limitations.md), and the [problem-statement migration note](docs/migration.md).
