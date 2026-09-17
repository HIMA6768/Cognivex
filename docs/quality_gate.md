# Image quality gate

## P5 contract

P5 runs only after P4 has accepted and normalized a supported still image. P4 answers “is this a valid supported image?” P5 answers “is this photograph usable enough for assessment?” The pure interface is `evaluate_quality(image, thresholds) -> QualityReport`.

`QualityReport` contains an overall `passed` flag, ordered per-check results, failed reason codes, and elapsed milliseconds. Each `QualityCheckResult` includes a stable check name, pass/fail state, numeric measurement, effective configured threshold, an optional machine-readable reason code, and safe remediation copy. Measurements are diagnostic data; the Streamlit UI presents remediation copy rather than raw values.

## Deterministic checks

P5 opens only P4's normalized session preview. RGBA previews are composited over white before measurement, then converted to grayscale. The image is proportionally reduced to a maximum 512-pixel side using bilinear resampling so runtime is bounded and deterministic.

| Check | Measurement | Fails when | Code |
| --- | --- | --- | --- |
| Blur | Global population variance of the four-neighbor discrete Laplacian plus the proportion of a fixed 4×4 spatial tile grid that clears the local sharpness floor | global variance is below `COGNIVEX_MIN_LAPLACIAN_VARIANCE` or fewer than `COGNIVEX_MIN_USABLE_SHARP_TILE_RATIO` of tiles clear `COGNIVEX_MIN_TILE_LAPLACIAN_VARIANCE` | `IMAGE_TOO_BLURRY` |
| Darkness | Mean and median grayscale luminance, plus the ratio of pixels below a configured dark cutoff | mean or median is below its minimum, or the dark-pixel ratio exceeds `COGNIVEX_MAX_DARK_PIXEL_RATIO` | `IMAGE_TOO_DARK` |
| Brightness | Mean and median grayscale luminance, plus the ratio of pixels above a configured bright cutoff | mean or median is above its maximum, or the bright-pixel ratio exceeds `COGNIVEX_MAX_BRIGHT_PIXEL_RATIO` | `IMAGE_TOO_BRIGHT` |

The sharp-tile ratio requires usable sharpness across enough spatial regions that localized text, graphics, or footer/banner edges cannot substitute for a clear vehicle scene. P5 does not detect, classify, or remove watermarks. The luminance median and tail ratios prevent a few headlights, reflections, or shadows from dominating a global mean. Every check runs, so a report can include several reasons. Equality at an applicable threshold passes, which makes configuration boundaries predictable. The `QualityCheckResult` records the robust primary diagnostic (the usable-sharp-tile ratio for blur and median luminance for exposure); the other configured criteria remain part of that check's pass/fail rule.

## Thresholds and tuning

| Variable | Default | Selection basis |
| --- | ---: | --- |
| `COGNIVEX_MIN_LAPLACIAN_VARIANCE` | `80.0` | Separates controlled sharp checkerboard and deliberately Gaussian-blurred fixtures using the documented measurement. |
| `COGNIVEX_MIN_TILE_LAPLACIAN_VARIANCE` | `40.0` | Requires typical spatial regions—not only a small high-edge region—to retain sharpness in controlled fixtures. |
| `COGNIVEX_MIN_USABLE_SHARP_TILE_RATIO` | `0.75` | Requires at least 75% of spatial tiles to clear the local sharpness floor; selected only against controlled overlay fixtures. |
| `COGNIVEX_MIN_MEAN_LUMINANCE` | `25.0` | Conservatively identifies near-black generated images on the 0–255 grayscale scale. |
| `COGNIVEX_MIN_MEDIAN_LUMINANCE` | `25.0` | Requires the typical pixel to clear the provisional darkness floor. |
| `COGNIVEX_DARK_PIXEL_LUMINANCE` | `20.0` | Defines the extreme-dark tail used by the dark-pixel ratio. |
| `COGNIVEX_MAX_DARK_PIXEL_RATIO` | `0.65` | Rejects scenes with a dominant extreme-dark pixel population. |
| `COGNIVEX_MAX_MEAN_LUMINANCE` | `230.0` | Conservatively identifies near-white generated images on the 0–255 grayscale scale. |
| `COGNIVEX_MAX_MEDIAN_LUMINANCE` | `230.0` | Requires the typical pixel to remain below the provisional overexposure ceiling. |
| `COGNIVEX_BRIGHT_PIXEL_LUMINANCE` | `240.0` | Defines the extreme-bright tail used by the bright-pixel ratio. |
| `COGNIVEX_MAX_BRIGHT_PIXEL_RATIO` | `0.65` | Rejects scenes with a dominant clipped/highlight pixel population. |

These are **PROVISIONAL ENGINEERING DEFAULTS**, not empirically validated thresholds for vehicle photos. Tune them through environment configuration only after the representative-photo protocol in [quality_threshold_calibration.md](quality_threshold_calibration.md); no implementation change is required. Do not treat a P5 pass as a prediction, decision, or claim outcome.

## Scope boundary

P5 does not repeat P4 validation and does not produce routing statuses, model confidence, OOD results, or localization. P8 separately maps P5/P7 contracts to development routing recommendations; P5 itself remains policy-free.

P6 defines those routing status values as schemas only. It does not select one or change P5 behavior.
