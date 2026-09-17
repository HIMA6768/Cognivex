# P6 Shared Schemas and Integration Contracts Design

## Goal

Freeze framework-independent Python contracts for the pre-model assessment pipeline. They let Streamlit, P4/P5, mock implementations, future ONNX/PyTorch adapters, P8 policy, and P9 presentation communicate without importing one another.

## Package and flow

`src/contracts/assessment.py` is the canonical schema module. It imports only the frozen label enums from `src.config.labels` and standard-library modules. It must not import Streamlit, Pillow, ONNX Runtime, PyTorch, or UI modules.

```
P4 ImageValidationResult.to_contract() → ValidationResult
P5 evaluate_quality()                 → QualityReport
P7 classification/localization        → ClassificationResult + LocalizationResult
P8 policy                              → RoutingDecision
P9 assembly                            → AssessmentResult
```

P4 keeps its existing upload-oriented result for UI compatibility and adds a lossless `to_contract()` adapter. P5 imports and re-exports the canonical quality types so its existing public imports remain compatible.

## Contracts

- `ValidationError`: stable string code and user-safe message.
- `ValidationResult`: pass/fail, optional P4 image digest/dimensions/normalized mode, and optional error.
- `QualityCheckResult` and `QualityReport`: P5's existing stable enums, values, messages, reasons, and elapsed time.
- `ModelMetadata`: non-empty model name; optional model version, experiment identifier, and preprocessing version; `MOCK` or `LIVE` mode. Optional metadata stays unset until the AI handoff; P6 does not invent versions.
- `ClassificationResult`: frozen severity and damage-type labels plus metadata, with no confidence or probability field.
- `Detection`: frozen damage type, absolute image-coordinate `BoundingBox`, optional uncalibrated score, and model metadata through its parent localization result. No label indexes, tensor names, shapes, or normalization settings are defined.
- `LocalizationResult`: zero or more detections and metadata.
- `RoutingReason`: a non-empty code/message pair without a policy-owned enum.
- `RoutingDecision`: one contract-only status (`FAST_TRACK_ELIGIBLE`, `HUMAN_REVIEW_REQUIRED`, or `RESUBMIT_IMAGE`) and a non-empty ordered collection of routing reasons. P6 does not choose a status.
- `AssessmentResult`: the aggregate, with optional P5/P7/P8 stages so partial pipeline progress is representable before P9.

All contracts are frozen, slot-backed dataclasses with JSON-compatible `to_dict()` output. They validate only structural integrity (non-empty identifiers, known labels, finite numeric values, valid bounding boxes); they do not define production confidence thresholds or routing rules.

## Quality calibration plan

The documented calibration plan keeps P5 values labelled **PROVISIONAL ENGINEERING DEFAULTS**. It calls for a consented, representative vehicle-photo evaluation set that includes normal daylight, low light, overexposure, motion/defocus blur, shadows, reflections, close/distant views, and varied body colors. Human reviewers will independently label assessment usability, then measure per-check false-accept and false-reject rates, inspect threshold-boundary cases, select operating points with documented trade-offs, and reserve a holdout set. Any approved changes are deployment configuration only and must be versioned with the dataset, labeling guidance, and results.

## Non-goals

P6 adds no inference, YOLO invocation, model artifact information, label indexes, tensor configuration, preprocessing numeric values, calibrated probabilities, confidence thresholds, routing policy, or result UI.
