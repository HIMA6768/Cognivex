# P1 Architecture and Configuration Design

## Goal

Establish the smallest safe Python/Streamlit application foundation for the
pre-model phase of Auto Insurance Damage Assessment from Photos. This
increment defines configuration and shared label contracts without training
models, fetching secrets, implementing UI, or guessing ONNX contracts.

## Architecture

The future Streamlit entrypoint will depend on reusable services under `src/`.
P1 creates the configuration boundary under `src/config/`; later increments
will consume it from validation, model adapters, decision logic, and pages.
Environment parsing is deterministic and side-effect free. Model-dependent
values remain unset until AI handoff; development-only image-quality defaults
are explicitly marked provisional.

## Decisions

- Streamlit remains the required UI technology.
- Python 3.11+ is the supported runtime for this foundation.
- Serving dependencies are kept separate from future training dependencies.
- Configuration is represented by frozen dataclasses, not UI widgets or model
  code.
- Severity and damage-type labels are canonical enums; model index mappings
  are intentionally not defined.
- Empty model paths and model thresholds are valid pre-model states.
- No live Vercel, Render, or MongoDB values are copied into source control.
- The existing root `env.example` is preserved as an unrelated architecture
  artifact until the team decides whether it should be removed or migrated.

## P1 acceptance criteria

- A project-specific Python dependency/configuration surface exists.
- `.env` and Streamlit secret files are ignored by Git.
- `.env.example` documents only safe Streamlit application variables.
- Environment parsing covers booleans, bounded numeric values, optional model
  values, and clear configuration errors.
- Canonical severity and damage-type labels are available without model
  artifacts.
- Tests cover defaults, overrides, invalid values, and unset handoff fields.
- README, setup, architecture, limitations, and implementation-log documents
  describe the actual pre-model state and pending AI handoff.

## Out of scope

- Streamlit pages or styling
- Image upload, validation, and quality implementation
- Classifier/localizer adapters
- Decision policy implementation
- ONNX runtime integration
- Production threshold calibration
- External service access or secret retrieval
