# P8 Policy-Only Routing Decision Engine Design

## Scope

P8 adds a deterministic, framework-independent policy that consumes the existing P5 `QualityReport`, P6 `ClassificationResult`/`LocalizationResult` contracts, and deployment policy configuration to return the existing P6 `RoutingDecision`. It performs no image processing, inference, UI rendering, persistence, insurance approval/rejection, or cost estimation.

## Selected design

The selected design is a small pure function, `evaluate_routing(classification, localization, quality_report, policy)`, supported by focused modules for reason vocabulary and localization conflicts. This is preferable to a class-based rule engine because P8 has a short fixed precedence order and no mutable lifecycle; it is preferable to embedding policy in Streamlit because contracts and tests must remain framework-independent.

`src/config/policy.py` owns **PROVISIONAL DEVELOPMENT POLICY** score thresholds and a deliberately small conflict-pair tuple. `src/decision/reasons.py` owns stable policy reason codes and user-safe text. `src/decision/conflicts.py` detects only configured classifier/localizer damage-type conflicts backed by localization scores at or above the configured conflict threshold. `src/decision/engine.py` owns precedence and returns P6 contracts.

## Precedence and reason ordering

1. Failed image quality returns `RESUBMIT_IMAGE` immediately. The decision includes `IMAGE_QUALITY_FAILED` followed by each failed P5 check code/message in P5 order.
2. Unavailable classification returns `HUMAN_REVIEW_REQUIRED` immediately with `CLASSIFICATION_UNAVAILABLE`.
3. Available classification accumulates human-review reasons in stable order: moderate/severe severity, missing or below-threshold severity score, missing or below-threshold damage-type score, then configured model-signal conflict.
4. If any accumulated reason exists, return `HUMAN_REVIEW_REQUIRED` with all reasons.
5. Otherwise, only a minor case with both scores at or above their thresholds returns `FAST_TRACK_ELIGIBLE` with `MINOR_HIGH_SCORE_ELIGIBLE`.

Threshold comparisons are inclusive at the boundary: a score equal to the threshold passes. Scores are model signals, not calibrated probabilities.

## Localization boundary

Localization is supplementary. `None`, unavailable localization, and zero detections do not change a valid classifier decision. A conflict exists only when a configured `(classifier damage type, localization damage type)` pair is present and the localization score meets the configured conflict threshold. The initial matrix contains only `scratch -> structural`, matching the explicit P8 example without inventing broad rules.

## Validation and safety

P6 contracts continue to reject malformed labels, scores, detections, and routing shapes. Policy configuration validates all thresholds as finite values in `[0, 1]` and validates conflict pairs as canonical, unequal damage labels. No `APPROVED`, `REJECTED`, or settlement state is introduced. Mock-derived decisions remain development/demo behavior.

## Verification

Table-driven unit tests cover every precedence branch, exact and immediately-below threshold boundaries, unavailable/empty localization, configured conflict, multiple ordered reasons, configuration-driven behavior, P7 mock compatibility, and existing contract validation. Completion requires focused P8 tests, the complete pytest suite, compile/dependency checks, and a Streamlit smoke test.
