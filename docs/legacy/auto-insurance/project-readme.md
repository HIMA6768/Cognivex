# Cognivex

Cognivex is a Python/Streamlit prototype for Auto Insurance Damage Assessment from Photos. P8 adds a pure development routing policy over the existing quality and mock-model contracts; it is not yet wired into the result UI.

## Current scope

The Streamlit shell provides five stable destinations:

1. Assessment
2. Model Comparison
3. Model Insights
4. Monitoring
5. System / About

It includes a responsive navy/slate visual system, accessible navigation and focus styles, clear empty states, and a persistent decision-support disclaimer. The Assessment page accepts one JPG/JPEG, PNG, or WEBP vehicle image; performs P4 structural validation and P5 deterministic blur/luminance checks; then retains its normalized preview for the Streamlit session.

`src/config/` exports application, upload, inference, quality, and `PolicySettings` contracts. `src.contracts` freezes independent validation, quality, classification, localization, routing, and aggregate-result contracts. `src.adapters` provides digest-stable P7 mocks marked `mock: true`; they are not real inference. `src.decision` implements P8 precedence, centralized reasons, and one narrow configured conflict rule. P5 values remain **PROVISIONAL ENGINEERING DEFAULTS** and P8 score cutoffs remain **PROVISIONAL DEVELOPMENT POLICY** defaults. Pending AI model handoff.

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

P8 does not implement real ONNX inference, YOLO/NMS, real model metadata, label indexes, calibrated thresholds, evaluation metrics, end-to-end orchestration, result rendering, monitoring integration, or production decisioning. The Streamlit Analyze Damage action remains a safe placeholder and does not display mock or routing output. The prototype is decision support only and cannot determine a claim outcome.

`.env.example` is a safe reference for local overrides; copying it to `.env` does not configure the application by itself. The existing root `env.example` is preserved user material from a conflicting architecture template and is not the active Streamlit configuration.

See the other files in this archive for the original setup, architecture, contracts, model integration, decision policy, image validation, quality gate, threshold calibration, UI design, user flow, and limitations documentation.
