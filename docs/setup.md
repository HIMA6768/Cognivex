# Setup

## Requirements

- Python 3.11 or newer
- Streamlit 1.39 or newer, below 2.0
- pytest for development verification
- pandas and scikit-learn only for optional data preparation

## Local setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pip install -e ".[dev,data-preparation]"
streamlit run app.py
```

Run the current suite with `pytest -q`.

## Environment

R2 consumes only:

```text
COGNIVEX_ENVIRONMENT
COGNIVEX_DEBUG
```

`.env.example` is a safe reference. The application reads process environment variables directly and does not automatically load `.env`. The canonical METABRIC paths are repository-relative and require no environment variable or external ZIP path. Preprocessing settings, model paths, and evaluation settings remain deferred.

No Vercel, MongoDB, external LLM, or model-service credentials are required.
