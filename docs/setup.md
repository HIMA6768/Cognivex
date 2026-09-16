# Setup

## Requirements

Use Python 3.11 or newer. Runtime dependencies are listed in `requirements.txt`. Pending AI model handoff.

## Local setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pip install pytest
pytest -q
```

The repository currently has no application entrypoint or inference command to launch. Do not fetch credentials or model artifacts for this increment.

## Environment

`.env.example` documents the six `COGNIVEX_*` variables consumed by `src/config/settings.py`; you may copy it to `.env` as a local reference. Copying it does not load values into the application: export or otherwise provide the needed values to the process environment before loading settings. Automatic dotenv loading is not part of P1, so `AppSettings.from_env()` remains side-effect-free. `.env` and Streamlit secrets are ignored by Git.

The root `env.example` is intentionally preserved but belongs to a conflicting, unrelated architecture template. Do not use it for this Streamlit foundation.
