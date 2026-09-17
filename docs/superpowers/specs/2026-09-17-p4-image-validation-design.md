# P4 Image Validation Design

## Goal

Make P3 uploads structurally safe and predictable before they reach the
preview. P4 validates a single supported still image without judging
photographic quality or invoking any AI-dependent behavior.

## Configuration

Existing `COGNIVEX_MIN_IMAGE_WIDTH` and `COGNIVEX_MIN_IMAGE_HEIGHT` provide
the minimum dimensions. P4 adds positive whole-number operational limits:

- `COGNIVEX_MAX_IMAGE_WIDTH=8192`
- `COGNIVEX_MAX_IMAGE_HEIGHT=8192`
- `COGNIVEX_MAX_IMAGE_PIXELS=40000000`

These are structural safety limits, not image-quality or AI thresholds. The
existing `COGNIVEX_MAX_UPLOAD_MB` limit remains the first byte-size check.

## Typed result contract

`validate_image_upload()` returns `ImageValidationResult`. Success includes a
`ValidatedImage` with safe display name, original bytes, normalized preview
bytes, digest, format, dimensions, source mode, normalized mode, alpha flag,
and EXIF-orientation metadata. Failure includes an `ImageValidationFailure`
with a stable uppercase machine code and a user-safe message.

The stable codes are `EMPTY_FILE`, `FILE_TOO_LARGE`, `UNSUPPORTED_FORMAT`,
`MIME_MISMATCH`, `FORMAT_MISMATCH`, `DECODE_FAILED`, `IMAGE_TOO_SMALL`,
`IMAGE_TOO_LARGE`, and `ANIMATED_IMAGE_NOT_SUPPORTED`.

## Validation order

1. Derive a display-only basename from the supplied filename; never create a
   path or storage key from it.
2. Check the JPG/JPEG/PNG/WEBP suffix allowlist, optional reported MIME, empty
   content, and configured byte limit.
3. Decode with Pillow under a decompression-bomb warning guard; verify actual
   decoded format matches the suffix.
4. Reject animated WebP or any future allowed animated format explicitly.
5. Inspect dimensions before loading pixels; reject below configured minimum,
   above configured width/height, or above configured pixel count.
6. Re-open safely, apply EXIF transpose, convert grayscale/palette/other
   opaque images to RGB and alpha-bearing images to RGBA, then create an
   in-memory PNG preview. No quality score is calculated.

## State and UI

P3 session keys, replacement behavior, reset behavior, and Analyze Damage
placeholder remain unchanged. The Assessment page passes configured structural
limits to the validator, displays `failure.message` through `st.error`, and
uses normalized preview bytes on success. No Python traceback is exposed.

## Explicit P5 boundary

P4 does not calculate blur, brightness, darkness, photographic quality, or
resubmission decisions. It does not add inference, YOLO, routing, decisions,
or any dependency on an AI handoff.
