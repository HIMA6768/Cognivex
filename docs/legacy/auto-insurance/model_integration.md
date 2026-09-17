# Model integration boundary

## P7 current implementation

P7 provides development-only, framework-independent adapters:

```text
MockClassifierAdapter  -> ClassificationResult
MockLocalizationAdapter -> LocalizationResult
```

They implement the same `ClassifierAdapter.predict(image)` and `LocalizationAdapter.localize(image)` protocols intended for future replacements:

```text
OnnxClassifierAdapter -> ClassificationResult
OnnxYoloAdapter       -> LocalizationResult
```

The protocols require only a P4-normalized image digest and dimensions. They do not import Streamlit, ONNX Runtime, PyTorch, or Pillow.

## Mock visibility and determinism

Every P7 adapter result contains `model.execution_mode: "MOCK"` and `model.mock: true`. A future result UI must display:

`MOCK INFERENCE — awaiting trained model handoff`

Mock labels, boxes, and scores are integration fixtures only; they are not evidence of model performance, real confidence, probability calibration, or suitability for claim decisions. P8 can consume these scores using explicitly provisional development thresholds, but the resulting route remains demo behavior rather than validated decision performance.

For the default scenario, the adapters calculate a SHA-256 digest of P4's stable image digest and use it to choose canonical labels and a zero/one/two detection layout. Explicit development scenarios provide normal minor/scratch, severe, low-score, unavailable classifier, and unavailable/no/one/multiple/disabled localization outputs. No unseeded randomness is used, so the same validated image produces the same output across reruns and processes.

Mock boxes are fixed fractional regions converted to the actual P4 normalized image dimensions, then clamped to valid in-bound coordinates. They are not YOLO boxes and have no NMS or post-processing semantics.

## Configuration

- `COGNIVEX_MOCK_INFERENCE=true` enables the development-only mock path.
- `COGNIVEX_LOCALIZATION_ENABLED=true` permits mock localization output.

P7 parses these flags but does not select or initialize a real model. Setting mock inference false causes a controlled unavailable result when passed into mock adapters; it does not activate real inference.

## Pending AI handoff

Real model names/versions, experiment IDs, preprocessing versions, label indexes, tensor interfaces, normalization, calibration, thresholds, model evaluation, ONNX Runtime, YOLO post-processing, and production deployment behavior remain pending AI handoff.
