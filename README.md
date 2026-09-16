# Cognivex

Cognivex is a Python/Streamlit foundation for Auto Insurance Damage Assessment from Photos. The repository is currently in the pre-model P1 phase: it defines configuration and shared labels, but has no Streamlit pages, inference integration, or production decision policy.

## Current scope

P1 provides a side-effect-free configuration boundary in `src/config/` and tests in `tests/test_config.py`. The exported contracts are `AppSettings`, `ThresholdSettings`, `SeverityLabel`, `DamageTypeLabel`, and `ConfigurationError`.

Model paths and model confidence are intentionally optional. Pending AI model handoff.

## Architecture

The planned application flow is Streamlit shell -> reusable services -> validation -> quality gate -> classifier -> localization -> decision engine -> result UI. Only the configuration foundation exists today; the downstream stages are future work.

## Setup

Requires Python 3.11 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pip install pytest
pytest -q
```

`.env.example` is a safe reference for local overrides; copying it to `.env` does not configure the application by itself. Export or otherwise provide the needed `COGNIVEX_*` values in the process environment before loading settings. P1 does not automatically load dotenv files. The existing root `env.example` is a preserved conflicting architecture template; it is not the active Streamlit configuration.

See [docs/setup.md](docs/setup.md), [docs/architecture.md](docs/architecture.md), and [docs/limitations.md](docs/limitations.md).
