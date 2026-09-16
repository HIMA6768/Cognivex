# Architecture

## Current state

The repository is a pre-model Python foundation. `src/config/` loads environment-backed settings through frozen dataclasses without external side effects. Canonical labels are defined independently of model artifacts. Tests are in `tests/test_config.py`.

## Planned flow

The future runtime is:

`Streamlit shell -> reusable services -> validation -> quality gate -> classifier -> localization -> decision engine -> result UI`

P1 implements none of those UI or inference stages. It establishes the boundary that later services can consume.

## Configuration contracts

- `AppSettings`: `environment`, `debug`, optional `model_path`, and nested `thresholds`; construct with `AppSettings.from_env(...)`.
- `ThresholdSettings`: optional `model_confidence`; provisional development image dimensions default to width `640` and height `480`.
- `SeverityLabel`: `minor`, `moderate`, `severe`.
- `DamageTypeLabel`: `dent`, `scratch`, `broken_glass`, `structural`.
- `ConfigurationError`: raised for invalid environment values.

The active safe variables are exactly:

```text
COGNIVEX_ENVIRONMENT
COGNIVEX_DEBUG
COGNIVEX_MODEL_PATH
COGNIVEX_MODEL_CONFIDENCE
COGNIVEX_MIN_IMAGE_WIDTH
COGNIVEX_MIN_IMAGE_HEIGHT
```

Model-dependent paths and confidence remain unset by default. Pending AI model handoff.

## Preserved template conflict

The existing root `env.example` describes an unrelated architecture involving Next.js, Vercel, MongoDB, and FastAPI. It is preserved user material and must not be treated as the active Streamlit configuration. The active template is `.env.example`.

