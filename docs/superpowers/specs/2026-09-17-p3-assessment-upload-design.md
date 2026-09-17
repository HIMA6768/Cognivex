# P3 Assessment Upload Design

## Goal

Add a safe, polished vehicle-image upload experience to the existing Streamlit
Assessment page without introducing image-quality decisions, model inference,
localization, routing, or mock predictions.

## Architecture

`src/config/uploads.py` will provide a small, frozen `UploadSettings` contract
with an operational upload-size limit. `AppSettings.from_env()` will expose it
alongside the existing threshold settings. `src/ui/upload_flow.py` will contain
pure upload validation and session-state helpers; the page will only render the
returned state. This keeps file-handling rules testable and prevents Streamlit
widgets from becoming a hidden assessment service.

## Upload contract

- `COGNIVEX_MAX_UPLOAD_MB` is a positive whole-number setting with a 10 MB
  development default. It is an upload-safety limit, not an AI threshold.
- The uploader accepts a single JPG/JPEG, PNG, or WEBP image.
- Validation checks the filename suffix, non-empty content, configured byte
  limit, supplied MIME type when present, and basic Pillow decode verification.
- The raw filename is display-only and is never used as a filesystem path.
- Invalid files display corrective guidance and never reach the preview or
  Analyze Damage action.

## State and interaction

The selected image is represented by immutable in-memory bytes, display name,
MIME type, and SHA-256 digest. It is stored under a namespaced session-state
key. Re-selecting the same image preserves the state; selecting a different
image clears the analysis-request flag. Reset removes the image, the analysis
flag, and the Streamlit uploader key before rerunning.

The Assessment page has three states:

1. Empty: an upload prompt, supported formats, size limit, and photo tips.
2. Invalid: a specific error and a reset/upload-another action.
3. Ready: a bordered preview card, Analyze Damage, and reset/upload-another.

Analyze Damage is intentionally a safe P3 placeholder. It confirms that the
image was accepted and explains that validation, quality assessment, inference,
localization, and routing are not yet implemented.

## Visual and accessibility requirements

The page keeps P2's neutral canvas, white surfaces, navy/slate hierarchy, blue
primary action, visible focus styles, and responsive stacking. The native
Streamlit uploader remains labelled and supports drag-and-drop. Guidance is
textual; errors state both the problem and the corrective action.

## Out of scope

- Minimum-dimension checks and quality-gate thresholds.
- Blur, brightness, and other quality scoring.
- Model, mock-model, YOLO, localization, decision, routing, or prediction UI.
- Uploaded-file persistence beyond the current Streamlit session.
- External storage, credentials, or services.

Pending AI model handoff.
