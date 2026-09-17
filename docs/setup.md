# Setup

## Requirements

Use Python 3.11 or newer. Runtime dependencies are listed in `requirements.txt`. Pending AI model handoff.

## Local setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pip install pytest
streamlit run app.py
```

In a second PowerShell window, run the test suite:

```powershell
pytest -q
```

The Streamlit shell accepts one structurally valid JPG/JPEG, PNG, or WEBP still vehicle image for a session-only normalized preview. P5 then runs deterministic blur and extreme-luminance checks before enabling the no-prediction Analyze Damage placeholder. It has no inference or external-service command. Do not fetch credentials or model artifacts for this increment.

## Environment

`.env.example` documents the twenty-six `COGNIVEX_*` variables consumed by `src/config/settings.py`; you may copy it to `.env` as a local reference. P5's quality variables are **PROVISIONAL ENGINEERING DEFAULTS**; P8's three `COGNIVEX_POLICY_*` score variables are **PROVISIONAL DEVELOPMENT POLICY** and are not calibrated probabilities. See [quality_gate.md](quality_gate.md) and [decision_policy.md](decision_policy.md). `COGNIVEX_MOCK_INFERENCE` and `COGNIVEX_LOCALIZATION_ENABLED` control development-only P7 mock availability; disabling mock inference does not activate a real model. Streamlit's native `server.maxUploadSize` remains 10 MB by default. Copying `.env.example` to `.env` does not automatically load it: provide values to the process environment before loading settings. `.env` and Streamlit secrets are ignored by Git.

The root `env.example` is intentionally preserved but belongs to a conflicting, unrelated architecture template. Do not use it for this Streamlit prototype.
