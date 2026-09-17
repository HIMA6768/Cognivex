# Image validation

## P4 structural contract

P4 determines whether one uploaded vehicle image is structurally safe to preview. It does not assess photographic quality and does not invoke a model, localization, routing, or decision engine.

The accepted filename suffixes are `.jpg`, `.jpeg`, `.png`, and `.webp`. Validation checks the supplied suffix and MIME type, non-empty content, configured byte limit, real Pillow decode, decoded format, still-image status, configured minimum dimensions, configured maximum width/height, and configured maximum pixel count. Uploaded filenames are reduced to a display-only basename; they are never used as storage paths.

## Stable error codes

| Code | Meaning | User action |
| --- | --- | --- |
| `EMPTY_FILE` | The upload has no bytes. | Choose another image. |
| `FILE_TOO_LARGE` | The bytes exceed the configured upload limit. | Choose a smaller file. |
| `UNSUPPORTED_FORMAT` | The suffix is not JPG/JPEG, PNG, or WEBP. | Export a supported still image. |
| `MIME_MISMATCH` | The reported browser MIME type conflicts with the suffix. | Upload the original image file. |
| `FORMAT_MISMATCH` | Decoded content conflicts with the filename extension. | Upload the original image file. |
| `DECODE_FAILED` | Pillow cannot safely verify or load the image. | Export the image again and retry. |
| `IMAGE_TOO_SMALL` | Width or height is below the configured minimum. | Upload a higher-resolution image. |
| `IMAGE_TOO_LARGE` | Width, height, or pixels exceed a configured structural limit. | Upload a smaller image. |
| `ANIMATED_IMAGE_NOT_SUPPORTED` | The file has multiple frames. | Upload a single still image. |

The Streamlit page renders only the user-safe message for a failure. It does not expose parser or Python tracebacks.

## Normalized preview behavior

After structural success, P4 reopens the image, applies EXIF orientation to the preview, and writes in-memory PNG preview bytes. Opaque images—including grayscale images—normalize to RGB. Images with alpha/transparency normalize to RGBA. The original uploaded bytes and SHA-256 digest remain in session state; no user file is written to disk.

Animated files are rejected rather than selecting a frame. The normalized preview is a UI safety/display representation, not an AI preprocessing specification. Pending AI model handoff.

## P5 boundary

P5 may add blur detection, brightness/darkness checks, photographic quality scoring, and quality-based resubmission behavior. P4 intentionally makes none of those judgments.
