# Cognivex

Cognivex is a Python/Streamlit prototype for Auto Insurance Damage Assessment from Photos. P7 adds deterministic development-only mock classification and localization adapters to the polished, pre-model application shell.

## Current scope

The Streamlit shell provides five stable destinations:

1. Assessment
2. Model Comparison
3. Model Insights
4. Monitoring
5. System / About

It includes a responsive navy/slate visual system, accessible navigation and focus styles, clear empty states, and a persistent decision-support disclaimer. The Assessment page accepts one JPG/JPEG, PNG, or WEBP vehicle image; performs P4 structural validation and P5 deterministic blur/luminance checks; then retains its normalized preview for the Streamlit session.

`src/config/` exports `AppSettings`, `ThresholdSettings`, `UploadSettings`, `InferenceSettings`, `SeverityLabel`, `DamageTypeLabel`, and `ConfigurationError`. `src.contracts` freezes independent validation, quality, classification, localization, routing, and aggregate-result contracts; `RoutingDecision` preserves an ordered collection of reasons, without selecting any policy outcome. `src.adapters` provides digest-stable P7 mocks marked `mock: true`; they are not real inference. P5 uses global and spatial-tile sharpness plus robust scene luminance statistics, all deployment-configurable **PROVISIONAL ENGINEERING DEFAULTS**, not calibrated vehicle-photo thresholds. Pending AI model handoff.

## Run locally

Requires Python 3.11 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pip install pytest
streamlit run app.py
```

Run the test suite with:

```powershell
pytest -q
```

## Current limitations

P7 does not implement real ONNX inference, YOLO/NMS, real model metadata, label indexes, routing policy, production thresholds, evaluation metrics, monitoring integration, or production decisioning. The Streamlit Analyze Damage action remains a safe placeholder and does not display mock output. The prototype is decision support only and cannot determine a claim outcome.

`.env.example` is a safe reference for local overrides; copying it to `.env` does not configure the application by itself. The existing root `env.example` is preserved user material from a conflicting architecture template and is not the active Streamlit configuration.

See [docs/setup.md](docs/setup.md), [docs/architecture.md](docs/architecture.md), [docs/api_contracts.md](docs/api_contracts.md), [docs/model_integration.md](docs/model_integration.md), [docs/image_validation.md](docs/image_validation.md), [docs/quality_gate.md](docs/quality_gate.md), [docs/quality_threshold_calibration.md](docs/quality_threshold_calibration.md), [docs/ui_design.md](docs/ui_design.md), [docs/user_flow.md](docs/user_flow.md), and [docs/limitations.md](docs/limitations.md).
