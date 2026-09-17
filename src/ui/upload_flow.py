"""Pure P4 structural validation and session-state contracts for image uploads."""

from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from io import BytesIO
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

from src.contracts.assessment import ValidationError, ValidationResult


UPLOAD_STATE_KEY = "assessment_upload"
ANALYSIS_REQUESTED_KEY = "assessment_analysis_requested"
ASSESSMENT_UPLOADER_KEY = "assessment_file_input"
RESET_UPLOAD_REQUESTED_KEY = "assessment_reset_requested"

_EXPECTED_MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}
_EXPECTED_PIL_FORMATS = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".webp": "WEBP",
}


class ImageValidationCode(str, Enum):
    """Stable machine-readable structural-validation codes."""

    EMPTY_FILE = "EMPTY_FILE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    MIME_MISMATCH = "MIME_MISMATCH"
    FORMAT_MISMATCH = "FORMAT_MISMATCH"
    DECODE_FAILED = "DECODE_FAILED"
    IMAGE_TOO_SMALL = "IMAGE_TOO_SMALL"
    IMAGE_TOO_LARGE = "IMAGE_TOO_LARGE"
    ANIMATED_IMAGE_NOT_SUPPORTED = "ANIMATED_IMAGE_NOT_SUPPORTED"


@dataclass(frozen=True, slots=True)
class ImageValidationLimits:
    """Configured structural limits used before image normalization."""

    min_width: int = 1
    min_height: int = 1
    max_width: int = 8192
    max_height: int = 8192
    max_pixels: int = 40_000_000


@dataclass(frozen=True, slots=True)
class ImageValidationFailure:
    """A stable error code paired with safe corrective text for the UI."""

    code: ImageValidationCode
    message: str


@dataclass(frozen=True, slots=True)
class ValidatedImage:
    """A structurally valid still image held only in the current session."""

    name: str
    mime_type: str | None
    data: bytes
    preview_data: bytes
    digest: str
    image_format: str
    width: int
    height: int
    source_mode: str
    normalized_mode: str
    has_alpha: bool
    orientation_applied: bool


@dataclass(frozen=True, slots=True)
class ImageValidationResult:
    """Exactly one structural-validation success or failure outcome."""

    image: ValidatedImage | None = None
    failure: ImageValidationFailure | None = None

    def to_contract(self) -> ValidationResult:
        """Adapt the P4 UI result to the framework-independent P6 contract."""
        if self.image is not None:
            return ValidationResult(
                passed=True,
                image_digest=self.image.digest,
                width=self.image.width,
                height=self.image.height,
                normalized_mode=self.image.normalized_mode,
                error=None,
            )
        if self.failure is not None:
            return ValidationResult(
                passed=False,
                image_digest=None,
                width=None,
                height=None,
                normalized_mode=None,
                error=ValidationError(code=self.failure.code.value, message=self.failure.message),
            )
        raise ValueError("ImageValidationResult must contain an image or failure")


def _failure(code: ImageValidationCode, message: str) -> ImageValidationResult:
    """Keep failure construction explicit and consistent across validation branches."""
    return ImageValidationResult(failure=ImageValidationFailure(code, message))


def _display_name(name: str) -> str:
    """Reduce an untrusted filename to a safe display-only basename."""
    basename = name.replace("\\", "/").rsplit("/", maxsplit=1)[-1].replace("\x00", "")
    return basename or "uploaded-image"


def _normalise_mime_type(mime_type: str | None) -> str | None:
    """Normalize optional browser MIME data without treating it as authoritative."""
    if not mime_type:
        return None
    return mime_type.lower().split(";", maxsplit=1)[0].strip() or None


def _open_verified_image(data: bytes) -> str | None:
    """Verify decodability once, returning the actual Pillow format when valid."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(BytesIO(data)) as image:
            image_format = image.format
            image.verify()
            return image_format


def validate_image_upload(
    name: str,
    mime_type: str | None,
    data: bytes,
    max_upload_bytes: int,
    limits: ImageValidationLimits,
) -> ImageValidationResult:
    """Validate and normalize one supported still image without quality or AI logic."""
    display_name = _display_name(name)
    suffix = "." + display_name.rsplit(".", maxsplit=1)[-1].lower() if "." in display_name else ""
    expected_mime = _EXPECTED_MIME_TYPES.get(suffix)
    if expected_mime is None:
        return _failure(
            ImageValidationCode.UNSUPPORTED_FORMAT,
            "Choose a JPG, JPEG, PNG, or WEBP image, then try again.",
        )

    normalized_mime = _normalise_mime_type(mime_type)
    if normalized_mime not in (None, "application/octet-stream", expected_mime):
        return _failure(
            ImageValidationCode.MIME_MISMATCH,
            "The file type does not match the selected image format. Upload the original image file.",
        )
    if not data:
        return _failure(
            ImageValidationCode.EMPTY_FILE,
            "The selected file is empty. Choose another vehicle image.",
        )
    if len(data) > max_upload_bytes:
        return _failure(
            ImageValidationCode.FILE_TOO_LARGE,
            "This image is larger than the configured upload limit. Choose a smaller file.",
        )

    try:
        image_format = _open_verified_image(data)
        if image_format != _EXPECTED_PIL_FORMATS[suffix]:
            return _failure(
                ImageValidationCode.FORMAT_MISMATCH,
                "The image content does not match its filename extension. Upload the original image file.",
            )

        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as source:
                if getattr(source, "is_animated", False) or getattr(source, "n_frames", 1) > 1:
                    return _failure(
                        ImageValidationCode.ANIMATED_IMAGE_NOT_SUPPORTED,
                        "Animated images are not supported. Upload a single still vehicle image.",
                    )

                source_mode = source.mode
                has_alpha = "A" in source.getbands() or "transparency" in source.info
                orientation_applied = source.getexif().get(274, 1) != 1
                oriented = ImageOps.exif_transpose(source)
                width, height = oriented.size
                if width < limits.min_width or height < limits.min_height:
                    return _failure(
                        ImageValidationCode.IMAGE_TOO_SMALL,
                        "This image is too small. Upload an image that is at least "
                        f"{limits.min_width} × {limits.min_height} pixels.",
                    )
                if (
                    width > limits.max_width
                    or height > limits.max_height
                    or width * height > limits.max_pixels
                ):
                    return _failure(
                        ImageValidationCode.IMAGE_TOO_LARGE,
                        "This image exceeds the configured dimension limit. Choose a smaller image.",
                    )

                normalized_mode = "RGBA" if has_alpha else "RGB"
                normalized = oriented.convert(normalized_mode)
                preview_buffer = BytesIO()
                normalized.save(preview_buffer, format="PNG")
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        UnidentifiedImageError,
        OSError,
        ValueError,
    ):
        return _failure(
            ImageValidationCode.DECODE_FAILED,
            "We could not read this image. Export it as JPG, PNG, or WEBP and upload it again.",
        )

    return ImageValidationResult(
        image=ValidatedImage(
            name=display_name,
            mime_type=normalized_mime,
            data=data,
            preview_data=preview_buffer.getvalue(),
            digest=sha256(data).hexdigest(),
            image_format=image_format or "",
            width=width,
            height=height,
            source_mode=source_mode,
            normalized_mode=normalized_mode,
            has_alpha=has_alpha,
            orientation_applied=orientation_applied,
        )
    )


def selected_upload(session_state: MutableMapping[str, object]) -> ValidatedImage | None:
    """Return the current validated upload without trusting arbitrary session data."""
    value = session_state.get(UPLOAD_STATE_KEY)
    return value if isinstance(value, ValidatedImage) else None


def store_upload(session_state: MutableMapping[str, object], image: ValidatedImage) -> None:
    """Persist an image and clear analysis intent only when the image changes."""
    current = selected_upload(session_state)
    if current is not None and current.digest == image.digest:
        return
    session_state[UPLOAD_STATE_KEY] = image
    session_state.pop(ANALYSIS_REQUESTED_KEY, None)


def reset_upload(session_state: MutableMapping[str, object]) -> None:
    """Clear all assessment-upload state, including Streamlit's upload widget value."""
    for key in (
        UPLOAD_STATE_KEY,
        ANALYSIS_REQUESTED_KEY,
        ASSESSMENT_UPLOADER_KEY,
        RESET_UPLOAD_REQUESTED_KEY,
    ):
        session_state.pop(key, None)
