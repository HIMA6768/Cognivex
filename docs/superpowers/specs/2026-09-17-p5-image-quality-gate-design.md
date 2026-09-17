# P5 Image Quality Gate Design

## Goal

Add a deterministic, non-AI quality gate after P4 structural validation. It answers whether a decoded, supported still image is photographically usable enough to continue in the prototype; it does not route, decide, infer, or score damage.

## Boundary and flow

```
Upload → P4 ImageValidator → P5 QualityGate → P7 Model Adapters → P8 Decision Engine
```

P5 accepts only `ValidatedImage` from `src.ui.upload_flow`. It reuses P4's normalized in-memory PNG preview and never parses an uploaded filename, checks extensions, decodes the original upload for validation, or duplicates P4's structural controls.

`evaluate_quality(image, thresholds)` returns a typed `QualityReport`, containing elapsed milliseconds, an overall `passed` flag, and an ordered result for each deterministic check. A failed result contains an uppercase stable reason code, its numeric measured value, the effective configured threshold, and safe remediation copy. The report deliberately does not contain a routing disposition.

## Measurements

P5 composites RGBA previews over solid white before measurement so transparent pixels do not become accidental black pixels. It converts to grayscale luminance and downsizes proportionally to a maximum 512-pixel side using deterministic bilinear resampling.

- **Blur:** population variance of the four-neighbor discrete Laplacian over interior grayscale pixels. Low variance means few local edges and fails `IMAGE_TOO_BLURRY`.
- **Darkness:** mean grayscale luminance below the configured inclusive minimum fails `IMAGE_TOO_DARK`.
- **Brightness:** mean grayscale luminance above the configured inclusive maximum fails `IMAGE_TOO_BRIGHT`.

All three checks always run, permitting multiple failures in one report. Exact threshold equality passes; only values below the dark minimum, above the bright maximum, or below the blur minimum fail.

## Configuration

`ThresholdSettings` receives these P5 values:

- `COGNIVEX_MIN_LAPLACIAN_VARIANCE=80.0`
- `COGNIVEX_MIN_MEAN_LUMINANCE=25.0`
- `COGNIVEX_MAX_MEAN_LUMINANCE=230.0`

The values are provisional engineering defaults selected to make deliberately uniform/blurred and near-black/near-white controlled fixtures distinguishable while avoiding a trained model or a claim of calibration. They are not empirically validated for real vehicle photographs. Future representative-image validation may tune them through deployment configuration without code changes.

## UI behavior

The Assessment page retains the P3/P4 upload, preview, reset, and session-state contracts. After P4 success it evaluates P5, shows one actionable error per failed quality check, preserves the preview, and disables the Analyze action when `passed` is false. A quality failure is informational gate feedback only: it does not perform `RESUBMIT_IMAGE` routing or generate any decision. A passing image allows Analyze Damage to retain the existing no-prediction placeholder.

## Tests

Tests use generated checkerboard, Gaussian-blurred, near-black, and near-white fixtures. They cover report shape/order, reason codes, exact threshold boundaries, simultaneous failures, threshold parsing and behavior changes, P3/P4 persistence/reset, and Streamlit error presentation.

## Explicit non-goals

No model execution, classifier confidence, OOD detection, YOLO, damage assessment, `FAST_TRACK_ELIGIBLE`, `HUMAN_REVIEW_REQUIRED`, `RESUBMIT_IMAGE`, routing, or production decision policy is added.
