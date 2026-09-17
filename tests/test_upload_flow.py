"""Pure P4 structural image-validation contracts."""

from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from src.ui.upload_flow import (
    ANALYSIS_REQUESTED_KEY,
    UPLOAD_STATE_KEY,
    ImageValidationCode,
    ImageValidationLimits,
    reset_upload,
    selected_upload,
    store_upload,
    validate_image_upload,
)


def _image_bytes(
    image_format: str,
    *,
    size: tuple[int, int] = (8, 8),
    mode: str = "RGB",
    orientation: int | None = None,
) -> bytes:
    """Create real image bytes with optional EXIF orientation for boundary tests."""
    buffer = BytesIO()
    image = Image.new(mode, size, color=(20, 40, 60, 128) if mode == "RGBA" else 60)
    save_options: dict[str, object] = {}
    if orientation is not None:
        exif = Image.Exif()
        exif[274] = orientation
        save_options["exif"] = exif
    image.save(buffer, format=image_format, **save_options)
    return buffer.getvalue()


def _animated_webp_bytes() -> bytes:
    """Create an actual two-frame WebP so animation detection is not mocked."""
    buffer = BytesIO()
    first = Image.new("RGB", (8, 8), color=(10, 20, 30))
    second = Image.new("RGB", (8, 8), color=(40, 50, 60))
    first.save(buffer, format="WEBP", save_all=True, append_images=[second], duration=100)
    return buffer.getvalue()


def _limits(**overrides: int) -> ImageValidationLimits:
    """Keep test structural limits independent from P4 implementation defaults."""
    values = {
        "min_width": 1,
        "min_height": 1,
        "max_width": 100,
        "max_height": 100,
        "max_pixels": 10_000,
    }
    values.update(overrides)
    return ImageValidationLimits(**values)


@pytest.mark.parametrize(
    ("name", "mime_type", "image_format"),
    [
        ("damage.jpg", "image/jpeg", "JPEG"),
        ("damage.jpeg", "image/jpeg", "JPEG"),
        ("damage.png", "image/png", "PNG"),
        ("damage.webp", "image/webp", "WEBP"),
    ],
)
def test_valid_supported_images_produce_typed_structural_metadata(
    name: str, mime_type: str, image_format: str
) -> None:
    """Dropping a supported format or metadata would break the P4 image contract."""
    result = validate_image_upload(
        name,
        mime_type,
        _image_bytes(image_format),
        max_upload_bytes=1024 * 1024,
        limits=_limits(),
    )

    assert result.failure is None
    assert result.image is not None
    assert result.image.name == name
    assert result.image.width == 8
    assert result.image.height == 8
    assert result.image.normalized_mode == "RGB"


@pytest.mark.parametrize(
    ("name", "mime_type", "payload", "expected_code"),
    [
        ("damage.gif", "image/gif", b"GIF89a", ImageValidationCode.UNSUPPORTED_FORMAT),
        ("damage.jpg", "image/png", _image_bytes("JPEG"), ImageValidationCode.MIME_MISMATCH),
        ("damage.jpg", "image/jpeg", b"", ImageValidationCode.EMPTY_FILE),
        ("damage.jpg", "image/jpeg", b"not-an-image", ImageValidationCode.DECODE_FAILED),
        (
            "damage.png",
            "image/png",
            _image_bytes("PNG")[:-12],
            ImageValidationCode.DECODE_FAILED,
        ),
        (
            "damage.jpg",
            "image/jpeg",
            _image_bytes("PNG"),
            ImageValidationCode.FORMAT_MISMATCH,
        ),
    ],
)
def test_invalid_uploads_return_stable_typed_error_codes(
    name: str,
    mime_type: str,
    payload: bytes,
    expected_code: ImageValidationCode,
) -> None:
    """Wrong rejection branches could otherwise expose malformed content to the UI."""
    result = validate_image_upload(
        name, mime_type, payload, max_upload_bytes=1024 * 1024, limits=_limits()
    )

    assert result.image is None
    assert result.failure is not None
    assert result.failure.code is expected_code
    assert result.failure.message


def test_pillow_decompression_bomb_protection_becomes_a_safe_decode_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pillow safety signals must not leak a traceback into the upload page."""
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1)

    result = validate_image_upload(
        "tiny.png",
        "image/png",
        _image_bytes("PNG"),
        max_upload_bytes=1024 * 1024,
        limits=_limits(),
    )

    assert result.image is None
    assert result.failure is not None
    assert result.failure.code is ImageValidationCode.DECODE_FAILED


def test_oversized_upload_is_rejected_before_decode() -> None:
    """Removing the byte limit would accept a payload the configured limit forbids."""
    result = validate_image_upload(
        "damage.jpg", "image/jpeg", _image_bytes("JPEG"), max_upload_bytes=1, limits=_limits()
    )

    assert result.failure is not None
    assert result.failure.code is ImageValidationCode.FILE_TOO_LARGE


@pytest.mark.parametrize(
    ("size", "limits", "expected_code"),
    [
        ((4, 8), _limits(min_width=5), ImageValidationCode.IMAGE_TOO_SMALL),
        ((8, 4), _limits(min_height=5), ImageValidationCode.IMAGE_TOO_SMALL),
        ((101, 8), _limits(), ImageValidationCode.IMAGE_TOO_LARGE),
        ((10, 10), _limits(max_pixels=99), ImageValidationCode.IMAGE_TOO_LARGE),
    ],
)
def test_dimension_limits_reject_images_outside_the_structural_envelope(
    size: tuple[int, int], limits: ImageValidationLimits, expected_code: ImageValidationCode
) -> None:
    """Skipping a dimension branch could allow unsafe or unusable image geometry through."""
    result = validate_image_upload(
        "damage.png",
        "image/png",
        _image_bytes("PNG", size=size),
        max_upload_bytes=1024 * 1024,
        limits=limits,
    )

    assert result.failure is not None
    assert result.failure.code is expected_code


def test_grayscale_and_rgba_images_receive_safe_normalized_preview_modes() -> None:
    """Leaving source modes unnormalized could make later preview and preprocessing inconsistent."""
    grayscale = validate_image_upload(
        "gray.png", "image/png", _image_bytes("PNG", mode="L"), 1024 * 1024, _limits()
    )
    rgba = validate_image_upload(
        "transparent.png", "image/png", _image_bytes("PNG", mode="RGBA"), 1024 * 1024, _limits()
    )

    assert grayscale.image is not None
    assert grayscale.image.normalized_mode == "RGB"
    assert Image.open(BytesIO(grayscale.image.preview_data)).mode == "RGB"
    assert rgba.image is not None
    assert rgba.image.normalized_mode == "RGBA"
    assert rgba.image.has_alpha is True
    assert Image.open(BytesIO(rgba.image.preview_data)).mode == "RGBA"


def test_orientation_is_applied_to_normalized_preview_without_trusting_filename_path() -> None:
    """Skipping EXIF transpose or retaining path fragments would make safe preview handling unreliable."""
    result = validate_image_upload(
        "../車 damage (1).jpg",
        "image/jpeg",
        _image_bytes("JPEG", size=(2, 3), orientation=6),
        1024 * 1024,
        _limits(),
    )

    assert result.image is not None
    assert result.image.name == "車 damage (1).jpg"
    assert result.image.orientation_applied is True
    assert (result.image.width, result.image.height) == (3, 2)
    assert Image.open(BytesIO(result.image.preview_data)).size == (3, 2)


def test_animated_webp_is_rejected_instead_of_selecting_an_arbitrary_frame() -> None:
    """Accepting animation silently would make assessment input nondeterministic."""
    result = validate_image_upload(
        "damage.webp", "image/webp", _animated_webp_bytes(), 1024 * 1024, _limits()
    )

    assert result.failure is not None
    assert result.failure.code is ImageValidationCode.ANIMATED_IMAGE_NOT_SUPPORTED


def test_same_selected_upload_survives_reruns_without_resetting_analysis() -> None:
    """Resetting state on an unchanged rerun would make the Analyze action unreliable."""
    result = validate_image_upload(
        "damage.png", "image/png", _image_bytes("PNG"), 1024 * 1024, _limits()
    )
    assert result.image is not None
    session: dict[str, object] = {}

    store_upload(session, result.image)
    session[ANALYSIS_REQUESTED_KEY] = True
    store_upload(session, result.image)

    assert selected_upload(session) == result.image
    assert session[ANALYSIS_REQUESTED_KEY] is True


def test_replacing_or_resetting_upload_clears_prior_analysis_state() -> None:
    """Keeping the old analysis flag after an image changes would misstate the current image."""
    first = validate_image_upload(
        "first.png", "image/png", _image_bytes("PNG"), 1024 * 1024, _limits()
    ).image
    second = validate_image_upload(
        "second.jpg", "image/jpeg", _image_bytes("JPEG"), 1024 * 1024, _limits()
    ).image
    assert first is not None
    assert second is not None
    session: dict[str, object] = {UPLOAD_STATE_KEY: first, ANALYSIS_REQUESTED_KEY: True}

    store_upload(session, second)
    assert selected_upload(session) == second
    assert ANALYSIS_REQUESTED_KEY not in session

    reset_upload(session)
    assert selected_upload(session) is None
    assert UPLOAD_STATE_KEY not in session
    assert ANALYSIS_REQUESTED_KEY not in session
