# P8 decision policy

## Boundary

P8 is a pure, deterministic decision-support policy:

```text
evaluate_routing(classification, localization, quality_report, policy)
  -> RoutingDecision
```

It consumes P5/P6/P7 contracts and returns the frozen P6 routing contract. It does not preprocess images, run a model, load artifacts, render Streamlit UI, access a database, estimate repair cost, or approve/reject/settle an insurance claim.

## Precedence

| Order | Condition | Status | Primary reason |
| ---: | --- | --- | --- |
| 1 | P5 quality failed | `RESUBMIT_IMAGE` | `IMAGE_QUALITY_FAILED`, followed by ordered P5 failure details |
| 2 | Classification unavailable | `HUMAN_REVIEW_REQUIRED` | `CLASSIFICATION_UNAVAILABLE` |
| 3 | Moderate severity | `HUMAN_REVIEW_REQUIRED` | `SEVERITY_MODERATE` |
| 4 | Severe severity | `HUMAN_REVIEW_REQUIRED` | `SEVERITY_SEVERE` |
| 5 | Missing/below-threshold severity or damage-type score | `HUMAN_REVIEW_REQUIRED` | score-specific reason(s) |
| 6 | Explicit configured classifier/localizer conflict | `HUMAN_REVIEW_REQUIRED` | `MODEL_SIGNAL_CONFLICT` |
| 7 | Minor, both scores at/above threshold, and no conflict | `FAST_TRACK_ELIGIBLE` | `MINOR_HIGH_SCORE_ELIGIBLE` |

Human-review reasons accumulate in this order so overlapping conditions are represented without changing the status. Quality failure and unavailable classification terminate evaluation at their higher precedence.

## Provisional configuration

| Variable | Default | Meaning |
| --- | ---: | --- |
| `COGNIVEX_POLICY_MIN_SEVERITY_SCORE` | `0.75` | Minimum severity signal for development fast-track eligibility |
| `COGNIVEX_POLICY_MIN_DAMAGE_TYPE_SCORE` | `0.75` | Minimum damage-type signal for development fast-track eligibility |
| `COGNIVEX_POLICY_MIN_LOCALIZATION_CONFLICT_SCORE` | `0.80` | Minimum localization signal considered by conflict policy |

These are **PROVISIONAL DEVELOPMENT POLICY** defaults. Scores are not calibrated probabilities, and the thresholds are not validated against real model calibration or insurance outcomes. Exact-threshold values pass; immediately lower values do not.

The initial conflict matrix contains only classifier `scratch` versus high-score localized `structural`. The matrix is centralized in `PolicySettings` and can be replaced programmatically without changing engine code. Localization that is absent, unavailable, or contains zero detections does not invalidate a successful classification.

## Mock and AI-handoff limitations

P7 mock inputs are accepted solely for deterministic integration development. Routing derived from them is demo behavior, not evidence of accuracy or decision performance. P8 does not detect non-vehicle images, out-of-distribution inputs, AI-generated images, or absence of visible damage because no validated upstream signal currently represents those conditions.
