# Setup

## Requirements

- Python 3.11 or newer
- Streamlit 1.39 or newer, below 2.0
- NumPy 2.x, pandas 3.x, and scikit-learn 1.5 or newer, below 2.0
- pytest for development verification

## Local setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pip install -e ".[dev]"
streamlit run app.py
```

Run the current suite with `pytest -q`.

## Environment

The active application configuration consumes only:

```text
COGNIVEX_ENVIRONMENT
COGNIVEX_DEBUG
```

`.env.example` is a safe reference. The application reads process environment variables directly and does not automatically load `.env`. The canonical METABRIC paths are repository-relative and require no environment variable or external ZIP path. R4 preprocessing policies come from canonical repository metadata rather than environment variables; model paths and evaluation settings remain deferred.

No Vercel, MongoDB, external LLM, or model-service credentials are required.
