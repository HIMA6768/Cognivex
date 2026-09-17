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

`.env.example` documents the twenty-three `COGNIVEX_*` variables consumed by `src/config/settings.py`; you may copy it to `.env` as a local reference. `COGNIVEX_MAX_UPLOAD_MB` defaults to `10` and controls the application-level maximum allowed upload size. `COGNIVEX_MIN_IMAGE_WIDTH`, `COGNIVEX_MIN_IMAGE_HEIGHT`, `COGNIVEX_MAX_IMAGE_WIDTH`, `COGNIVEX_MAX_IMAGE_HEIGHT`, and `COGNIVEX_MAX_IMAGE_PIXELS` set structural geometry limits only. P5's global/tile Laplacian, usable-sharp-tile ratio, mean/median luminance, and dark/bright-tail variables tune the quality gate without code edits; see [quality_gate.md](quality_gate.md) for the full list. All defaults are **PROVISIONAL ENGINEERING DEFAULTS** and must be evaluated on representative vehicle images before production use. `COGNIVEX_MOCK_INFERENCE` and `COGNIVEX_LOCALIZATION_ENABLED` control development-only P7 mock availability; disabling mock inference does not activate a real model. Streamlit's native `server.maxUploadSize` is also set to 10 MB in `.streamlit/config.toml`; keep the two values aligned when changing the deployment limit. Copying the file does not load values into the application: export or otherwise provide the needed values to the process environment before loading settings. Automatic dotenv loading is not part of this prototype, so `AppSettings.from_env()` remains side-effect-free. `.env` and Streamlit secrets are ignored by Git.

The root `env.example` is intentionally preserved but belongs to a conflicting, unrelated architecture template. Do not use it for this Streamlit prototype.
