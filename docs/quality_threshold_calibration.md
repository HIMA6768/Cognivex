# Quality-threshold calibration plan

## Current state

`COGNIVEX_MIN_LAPLACIAN_VARIANCE=80.0`, `COGNIVEX_MIN_TILE_LAPLACIAN_VARIANCE=40.0`, `COGNIVEX_MIN_USABLE_SHARP_TILE_RATIO=0.75`, `COGNIVEX_MIN_MEAN_LUMINANCE=25.0`, `COGNIVEX_MIN_MEDIAN_LUMINANCE=25.0`, `COGNIVEX_DARK_PIXEL_LUMINANCE=20.0`, `COGNIVEX_MAX_DARK_PIXEL_RATIO=0.65`, `COGNIVEX_MAX_MEAN_LUMINANCE=230.0`, `COGNIVEX_MAX_MEDIAN_LUMINANCE=230.0`, `COGNIVEX_BRIGHT_PIXEL_LUMINANCE=240.0`, and `COGNIVEX_MAX_BRIGHT_PIXEL_RATIO=0.65` are **PROVISIONAL ENGINEERING DEFAULTS**. They were selected against controlled generated fixtures only. They are not validated vehicle-photo thresholds and must not support a production claim or routing outcome.

## Evaluation set

Build a consented, access-controlled vehicle-photo set with documented source, usage permission, capture conditions, and split assignment. Include normal daylight, low light, overexposure, motion blur, defocus blur, shadows, reflections, close-up damage, distant vehicle views, and multiple body colors. Stratify examples so each factor is represented across damage types and severities where feasible; keep near-threshold images rather than filtering them out.

Use separate development, tuning, and untouched holdout partitions. Do not allow duplicate captures of the same vehicle/event to cross partitions.

## Labels and review

At least two independent reviewers label each photo as usable or unusable for preliminary damage assessment and identify blur, darkness, brightness, or multiple causes. Resolve disagreement with documented adjudication while retaining the original reviewer labels and agreement metrics.

Reviewers assess image usability only. They do not make coverage, repair, fraud, or claim decisions.

## Analysis and selection

1. Run the unchanged P5 metric implementation against every image and retain global sharpness, per-tile sharpness, the usable-sharp-tile ratio, mean and median luminance, dark/bright tail ratios, report codes, processing version, and runtime.
2. Compare P5 outcomes with adjudicated usability labels; report false accepts, false rejects, sensitivity, specificity, and confusion matrices separately for each capture condition.
3. Inspect misclassifications and threshold-boundary images by condition, body color, distance, reflection, and shadow subgroup.
4. Choose candidate thresholds using documented usability trade-offs, then evaluate them once on the untouched holdout set.
5. Record the selected configuration, dataset version, labeling guide, reviewers, date, implementation version, and holdout results in a versioned evaluation artifact.

## Change control

Threshold changes must be configuration-only changes, reviewed with the evaluation artifact and a regression suite covering representative boundary fixtures. Update `.env.example`, setup documentation, and the release record together. Do not present any tuning as empirical validation until the representative evaluation and holdout analysis are complete.
