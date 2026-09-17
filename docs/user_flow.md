# User flow

## Current P5 experience

1. Open the local Streamlit application with `streamlit run app.py`.
2. Review the persistent prototype status and decision-support disclaimer.
3. Use the sidebar to move among Assessment, Model Comparison, Model Insights, Monitoring, and System / About.
4. On Assessment, drag and drop or browse for one JPG/JPEG, PNG, or WEBP still vehicle image. Review the size limit and photo tips before uploading.
5. P4 validates the file's real decoded format, configured byte and geometry limits, still-image status, and safe orientation/mode handling.
6. P5 then measures global and spatial-tile blur plus robust scene luminance (mean, median, and extreme-pixel ratios) on the normalized preview using provisional configured thresholds.
7. If P5 passes, review the session-only normalized preview and select Analyze Damage to confirm the safe no-prediction boundary. If it fails, read every corrective message, retain the preview for reference, and use Upload another image.
8. If the file is unsupported, oversized, empty, MIME/format-inconsistent, malformed, animated, undersized, or exceeds dimension limits, follow the corrective message and upload another image.
9. On Model Comparison and Model Insights, see the honest pending/unavailable states rather than invented evaluation data.
10. On Monitoring, see the zero-data development state.
11. On System / About, review the planned flow: Upload -> Validation -> Quality Gate -> Classifier -> YOLO localization -> Decision Engine -> Routing.

## What does not happen yet

P5 does not execute a model; localize damage; apply routing; render a result; make a claim decision; or turn a quality failure into a resubmission disposition. Candidate models—Custom CNN, MobileNetV2, ViT-Tiny, and planned YOLOv8n localization—remain under evaluation. Pending AI model handoff.

## Increment boundary

P8 remains a separate routing-policy increment. This quality gate only reports quality observations; it does not select a routing status. P5 thresholds need representative vehicle-image evaluation before any production use.
