# Assessment API contracts

## Purpose

`src.contracts.assessment` is the P6 canonical, framework-independent schema surface. Its frozen, slot-backed dataclasses expose JSON-compatible `to_dict()` results and import no Streamlit, Pillow, ONNX Runtime, or PyTorch code.

## Pipeline contracts

| Stage | Contract | Required contents | Current producer |
| --- | --- | --- | --- |
| P4 | `ValidationResult` | pass/fail, normalized image metadata or `ValidationError` | `ImageValidationResult.to_contract()` |
| P5 | `QualityReport` | overall state, ordered checks, reason codes, latency | `evaluate_quality()` |
| P7 | `ClassificationResult` | frozen severity/damage labels and `ModelMetadata` | Pending AI handoff |
| P7 | `LocalizationResult` | `Detection` list and `ModelMetadata` | Pending AI handoff |
| P8 | `RoutingDecision` | contract status and ordered `RoutingReason` collection | `evaluate_routing()` |
| P9 | `AssessmentResult` | aggregate of each stage; downstream entries are optional | Pending result increment |

`AssessmentResult` permits optional P5–P8 entries so a partial pipeline can be serialized safely while later stages are pending.

## Labels and statuses

Available `ClassificationResult.severity` accepts only `SeverityLabel`: `minor`, `moderate`, or `severe`. Available `damage_type` and `Detection.damage_type` accept only `DamageTypeLabel`: `dent`, `scratch`, `broken_glass`, or `structural`. Classification can instead be explicitly unavailable, with no fabricated labels and a non-empty unavailable reason. P7 may provide `severity_score`, `damage_type_score`, and `all_scores`; those are illustrative mock scores, not calibrated probabilities or P8 thresholds.

`RoutingDecision.status` accepts only these P8 policy-output values:

- `FAST_TRACK_ELIGIBLE`
- `HUMAN_REVIEW_REQUIRED`
- `RESUBMIT_IMAGE`

`RoutingDecision.reasons` is a required, non-empty ordered tuple of `RoutingReason` values. P8 supplies the controlled reason vocabulary and deterministic precedence documented in [decision_policy.md](decision_policy.md), while P6 remains policy-free.

## Model provenance

`ModelMetadata` carries a non-empty model name, optional model version, experiment ID, preprocessing version, `MOCK`/`LIVE` execution mode, and serialized `mock` boolean derived from that mode. Optional fields must remain `None` until a verified AI handoff supplies them. P6/P7 intentionally define no label indexes, tensor names, input shapes, normalization values, real model versions, calibrated probabilities, or confidence thresholds.

`Detection` uses an absolute-coordinate `BoundingBox` in P4 orientation-normalized image coordinates. `LocalizationResult` can be available with zero detections or explicitly unavailable with a reason and no detections. Detection scores have no calibrated or policy meaning.

## Compatibility

P4 preserves its `ImageValidationResult` UI contract and exposes `to_contract()` as a lossless conversion to `ValidationResult`. P5 imports the canonical `QualityReport`, `QualityCheckResult`, and quality enums from this module, retaining its existing public re-exports. Contracts have no widget state or runtime-specific model types, which keeps mocks and later adapters easy to construct in tests.
