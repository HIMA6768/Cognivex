# Architecture

## Current state

The repository is a pre-model Python/Streamlit prototype. `app.py` is a thin entrypoint that configures Streamlit and delegates to `src/ui/shell.py`. The shell applies the package-owned visual theme, renders typed navigation, and dispatches to page modules. The Assessment page consumes pure P4 structural validation/session-state helpers and pure P5 quality reports; it does not access a model or external service. `src/contracts/assessment.py` freezes independent cross-stage types, and `src/adapters/` contains isolated P7 development mocks. `src/config/` loads environment-backed settings through frozen dataclasses without external side effects.

## Planned flow

The planned runtime is:

`Upload -> Validation -> Quality Gate -> Classifier -> YOLO localization -> Decision Engine -> Routing`

P4 implements a single still-image upload, actual decode/format validation, configured byte and geometry limits, decompression safeguards, session-only retention, EXIF-aware RGB/RGBA preview normalization, and invalid-file guidance. P5 evaluates the P4 preview with deterministic blur and extreme-luminance checks before enabling the existing no-prediction placeholder. P6 freezes P4–P9 data contracts. P7 adds mock-only classifier/localizer implementations under those contracts; they remain outside the Streamlit assessment path. Real model execution, localization, decisioning, routing, results, and external-service behavior remain unimplemented.

## UI composition

- `src/ui/theme.py` owns static design tokens and scoped CSS.
- `src/ui/navigation.py` owns the stable `Page` metadata and sidebar selection.
- `src/ui/components/layout.py` owns safe page headers, empty states, and shell status.
- `src/ui/upload_flow.py` owns pure structural validation, normalized preview construction, and session-state transitions.
- `src/ui/quality_gate.py` owns P5 deterministic quality measurements and typed reports.
- `src/contracts/assessment.py` owns P6 cross-stage schemas and JSON-compatible serialization.
- `src/adapters/interfaces.py` owns replacement-safe P7 adapter protocols.
- `src/adapters/mock.py` owns deterministic mock-only P7 behavior.
- `src/ui/shell.py` owns page dispatch through `PAGE_RENDERERS`.
- `src/ui/pages/` owns presentation-only content for the five destinations.

The shell does not read model artifacts, call external services, or implement assessment logic. Uploaded bytes are held only in Streamlit session state and the displayed filename is never used as a server-side path.

## Configuration contracts

- `AppSettings`: `environment`, `debug`, optional `model_path`, and nested `thresholds` and `upload` settings; construct with `AppSettings.from_env(...)`.
- `ThresholdSettings`: optional `model_confidence`; structural image dimensions default to minimum `640 × 480`, maximum `8192 × 8192`, and `40,000,000` pixels; P5 defaults combine global Laplacian variance `80.0`, a `0.75` usable-sharp-tile ratio over a 4×4 grid with a local floor of `40.0`, mean/median luminance `25.0`–`230.0`, and configurable extreme dark/bright tail ratios.
- `UploadSettings`: operational `max_upload_mb` limit, defaulting to `10`; it is not an AI threshold.
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
COGNIVEX_MAX_UPLOAD_MB
COGNIVEX_MAX_IMAGE_WIDTH
COGNIVEX_MAX_IMAGE_HEIGHT
COGNIVEX_MAX_IMAGE_PIXELS
COGNIVEX_MIN_LAPLACIAN_VARIANCE
COGNIVEX_MIN_TILE_LAPLACIAN_VARIANCE
COGNIVEX_MIN_USABLE_SHARP_TILE_RATIO
COGNIVEX_MIN_MEAN_LUMINANCE
COGNIVEX_MIN_MEDIAN_LUMINANCE
COGNIVEX_DARK_PIXEL_LUMINANCE
COGNIVEX_MAX_DARK_PIXEL_RATIO
COGNIVEX_MAX_MEAN_LUMINANCE
COGNIVEX_MAX_MEDIAN_LUMINANCE
COGNIVEX_BRIGHT_PIXEL_LUMINANCE
COGNIVEX_MAX_BRIGHT_PIXEL_RATIO
COGNIVEX_MOCK_INFERENCE
COGNIVEX_LOCALIZATION_ENABLED
```

Model-dependent paths and confidence remain unset by default. P4 validation checks allowed suffix/type, non-empty bytes, configured size, actual decoded format, still-image status, dimensions, pixels, and safely normalizes orientation/mode for preview. P5 accepts only that normalized preview, composites transparency over white, measures bounded global and tile-based grayscale Laplacian variance plus mean/median luminance and extreme-pixel ratios, and returns a report without a routing disposition. P6 adds independent `ValidationResult`, `QualityReport`, classification/localization, routing, and aggregate contracts; `RoutingDecision` has a required ordered `reasons` collection but no policy implementation. P7 adds `InferenceSettings` (`COGNIVEX_MOCK_INFERENCE`, `COGNIVEX_LOCALIZATION_ENABLED`) and mock-only adapters marked with serialized `mock: true`; real model identifiers and preprocessing fields remain optional pending the AI handoff. The native Streamlit server upload limit is set to the same 10 MB default in `.streamlit/config.toml`; operators must keep both values aligned when overriding the limit. P5 thresholds are **PROVISIONAL ENGINEERING DEFAULTS** rather than calibrated vehicle-photo thresholds. Pending AI model handoff.

## Model evaluation status

Candidate model families are Custom CNN, MobileNetV2, ViT-Tiny, and planned YOLOv8n localization. There are no evaluation results, metrics, preprocessing contracts, label-index mappings, thresholds, or final model selection. Pending AI model handoff.

## Preserved template conflict

The existing root `env.example` describes an unrelated architecture involving Next.js, Vercel, MongoDB, and FastAPI. It is preserved user material and must not be treated as the active Streamlit configuration. The active template is `.env.example`.
