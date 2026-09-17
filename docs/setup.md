# Setup

## Requirements

- Python 3.11 or newer
- Streamlit 1.39 or newer, below 2.0
- pytest for development verification

## Local setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pip install pytest
streamlit run app.py
```

Run the current suite with `pytest -q`.

## Environment

R1 consumes only:

```text
COGNIVEX_ENVIRONMENT
COGNIVEX_DEBUG
```

`.env.example` is a safe reference. The application reads process environment variables directly and does not automatically load `.env`. Dataset paths, upload limits, schema mappings, subtype labels, preprocessing settings, model paths, and evaluation settings are deferred until their implementing increment.

No Vercel, MongoDB, external LLM, or model-service credentials are required.
