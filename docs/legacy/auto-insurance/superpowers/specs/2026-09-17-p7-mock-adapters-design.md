# P7 Deterministic Mock Classification and Localization Adapters Design

## Goal

Provide deterministic, runtime-independent P7 mock adapters that satisfy the P6 schema surface and can be replaced by ONNX adapters without changing their callers.

## Interfaces and inputs

`src/adapters/interfaces.py` defines structural `AssessmentImage` input requirements (`digest`, `width`, `height`), `ClassifierAdapter.predict(image) -> ClassificationResult`, and `LocalizationAdapter.localize(image) -> LocalizationResult`. It imports no Streamlit, Pillow, ONNX Runtime, or PyTorch. P4 `ValidatedImage` conforms structurally.

`MockClassifierAdapter` and `MockLocalizationAdapter` live in `src/adapters/mock.py`. A SHA-256-derived index over the stable P4 digest selects default labels and detection layout, ensuring repeatability across reruns and processes. Explicit scenarios are available only for development/test coverage: normal minor/scratch, severe, low score, classifier unavailable, one/no/multiple detections, localization unavailable, and localization disabled.

## P6 extensions

`ModelMetadata` gains serialized `mock: bool`, derived from `execution_mode`, so mock output visibly contains `mock: true`. `ClassificationResult` gains optional illustrative severity/damage scores and a tuple of `LabelScore` entries, plus availability state. `LocalizationResult` gains availability state. An unavailable result carries no invented labels/detections and a non-empty safe reason.

Scores are normalized deterministic mock display values, explicitly not probabilities, calibrated confidence, or decision thresholds. P7 returns all frozen canonical severity and damage labels in `all_scores` for available classification results.

## Geometry

Mock localization boxes are computed as fixed fractional regions of actual P4 normalized image dimensions, rounded and clamped to valid positive interior bounds. They are therefore deterministic and inside real image boundaries. They do not represent YOLO output, NMS, or real localization behavior.

## Configuration

`InferenceSettings` adds `COGNIVEX_MOCK_INFERENCE=true` and `COGNIVEX_LOCALIZATION_ENABLED=true`. The flags are parsed but do not activate a real adapter. A future composition root can select `MockClassifierAdapter` versus `OnnxClassifierAdapter` and `MockLocalizationAdapter` versus `OnnxYoloAdapter` while preserving P6 types.

## Non-goals

No ONNX Runtime, PyTorch, YOLO, NMS, real class-index mapping, preprocessing normalization, decision/routing policy, repair estimation, real confidence threshold, or Streamlit result integration is added.
