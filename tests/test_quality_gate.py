"""Deterministic P5 contracts for post-P4 image quality evaluation."""

from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageFilter

from src.ui.quality_gate import (
    QualityCheckName,
    QualityReasonCode,
    QualityThresholds,
    evaluate_quality,
)
from src.ui.upload_flow import ImageValidationLimits, validate_image_upload


def _validated_image(image: Image.Image):
    """Produce a real P4 output so P5 consumes only its public boundary."""
    payload = BytesIO()
    image.save(payload, format="PNG")
    result = validate_image_upload(
        "vehicle.png",
        "image/png",
        payload.getvalue(),
        max_upload_bytes=1024 * 1024,
        limits=ImageValidationLimits(
            min_width=1,
            min_height=1,
            max_width=1024,
            max_height=1024,
            max_pixels=1_000_000,
        ),
    )
    assert result.image is not None
    return result.image


def _checkerboard(size: int = 64) -> Image.Image:
    """Create a hand-controlled sharp fixture with abundant local edges."""
    image = Image.new("L", (size, size), color=0)
    pixels = image.load()
    for y in range(size):
        for x in range(size):
            pixels[x, y] = 255 if (x // 4 + y // 4) % 2 else 0
    return image.convert("RGB")


def _blurred_scene_with_sharp_overlay_edges() -> Image.Image:
    """Simulate a blurred scene with sharp center graphics and a sharp footer banner."""
    scene = _checkerboard(192).filter(ImageFilter.GaussianBlur(radius=6)).convert("L")
    scene.paste(_checkerboard(96).convert("L"), (48, 48))
    scene.paste(_checkerboard(192).convert("L").crop((0, 0, 192, 48)), (0, 144))
    return scene.convert("RGB")


def _thresholds(**overrides: float) -> QualityThresholds:
    values = {
        "min_laplacian_variance": 80.0,
        "min_tile_laplacian_variance": 40.0,
        "min_usable_sharp_tile_ratio": 0.75,
        "min_mean_luminance": 25.0,
        "min_median_luminance": 25.0,
        "dark_pixel_luminance": 20.0,
        "max_dark_pixel_ratio": 0.65,
        "max_mean_luminance": 230.0,
        "max_median_luminance": 230.0,
        "bright_pixel_luminance": 240.0,
        "max_bright_pixel_ratio": 0.65,
    }
    values.update(overrides)
    return QualityThresholds(**values)


def _check(report, name: QualityCheckName):
    return next(check for check in report.checks if check.name is name)


def test_sharp_normally_lit_image_passes_every_quality_check() -> None:
    """Removing an actual quality measurement would allow a bad gate to pass silently."""
    report = evaluate_quality(_validated_image(_checkerboard()), _thresholds())

    assert report.passed is True
    assert report.reasons == ()
    assert [check.name for check in report.checks] == [
        QualityCheckName.BLUR,
        QualityCheckName.DARKNESS,
        QualityCheckName.BRIGHTNESS,
    ]
    assert all(check.passed for check in report.checks)
    assert report.elapsed_ms >= 0


def test_deliberately_blurred_image_fails_with_actionable_stable_reason() -> None:
    """Dropping the Laplacian check would permit an intentionally defocused fixture."""
    blurred = _checkerboard().filter(ImageFilter.GaussianBlur(radius=5))
    report = evaluate_quality(_validated_image(blurred), _thresholds())
    blur = _check(report, QualityCheckName.BLUR)

    assert report.passed is False
    assert blur.passed is False
    assert blur.code is QualityReasonCode.IMAGE_TOO_BLURRY
    assert blur.measured_value < blur.threshold
    assert blur.message == (
        "The image appears too blurry for a reliable assessment. Please upload a sharper "
        "photo and keep the damaged area in focus."
    )


def test_localized_sharp_graphics_do_not_allow_a_blurred_scene_to_pass() -> None:
    """A sharp watermark-sized region must not conceal blur across the rest of the photograph."""
    blurred_scene = _checkerboard(128).filter(ImageFilter.GaussianBlur(radius=6)).convert("L")
    sharp_patch = _checkerboard(32).convert("L")
    blurred_scene.paste(sharp_patch, (0, 0))

    report = evaluate_quality(_validated_image(blurred_scene.convert("RGB")), _thresholds())
    blur = _check(report, QualityCheckName.BLUR)

    assert blur.passed is False
    assert blur.code is QualityReasonCode.IMAGE_TOO_BLURRY


def test_blurred_scene_with_sharp_overlay_edges_and_footer_still_fails() -> None:
    """Overlay-heavy synthetic edges must not substitute for scene-level vehicle sharpness."""
    report = evaluate_quality(_validated_image(_blurred_scene_with_sharp_overlay_edges()), _thresholds())
    blur = _check(report, QualityCheckName.BLUR)

    assert blur.passed is False
    assert blur.code is QualityReasonCode.IMAGE_TOO_BLURRY


def test_usable_sharp_tile_ratio_is_tunable_without_code_changes() -> None:
    """Operators can tune the scene-coverage requirement without changing the metric code."""
    image = _validated_image(_blurred_scene_with_sharp_overlay_edges())
    permissive = evaluate_quality(image, _thresholds(min_usable_sharp_tile_ratio=0.5))
    strict = evaluate_quality(image, _thresholds(min_usable_sharp_tile_ratio=0.75))

    assert _check(permissive, QualityCheckName.BLUR).passed is True
    assert _check(strict, QualityCheckName.BLUR).passed is False


def test_near_black_image_includes_the_darkness_failure() -> None:
    """Removing the luminance lower bound would accept unusably dark photographs."""
    report = evaluate_quality(_validated_image(Image.new("RGB", (64, 64), color=(3, 3, 3))), _thresholds())
    darkness = _check(report, QualityCheckName.DARKNESS)

    assert report.passed is False
    assert darkness.code is QualityReasonCode.IMAGE_TOO_DARK
    assert darkness.measured_value < darkness.threshold
    assert "better lighting" in (darkness.message or "")


def test_near_white_image_includes_the_brightness_failure() -> None:
    """Removing the luminance upper bound would accept overexposed photographs."""
    report = evaluate_quality(_validated_image(Image.new("RGB", (64, 64), color=(252, 252, 252))), _thresholds())
    brightness = _check(report, QualityCheckName.BRIGHTNESS)

    assert report.passed is False
    assert brightness.code is QualityReasonCode.IMAGE_TOO_BRIGHT
    assert brightness.measured_value > brightness.threshold
    assert "reduce overexposure" in (brightness.message or "")


def test_dark_scene_with_bright_highlights_still_fails_darkness() -> None:
    """A few headlights must not make a predominantly unusable night scene pass."""
    night_scene = Image.new("L", (128, 128), color=5)
    night_scene.paste(Image.new("L", (48, 48), color=255), (40, 40))
    report = evaluate_quality(
        _validated_image(night_scene.convert("RGB")),
        _thresholds(min_laplacian_variance=0.0, min_tile_laplacian_variance=0.0),
    )
    darkness = _check(report, QualityCheckName.DARKNESS)

    assert darkness.passed is False
    assert darkness.code is QualityReasonCode.IMAGE_TOO_DARK


def test_mostly_overexposed_scene_with_dark_details_still_fails_brightness() -> None:
    """A few dark details must not make a predominantly clipped image pass exposure checks."""
    overexposed_scene = Image.new("L", (128, 128), color=250)
    overexposed_scene.paste(Image.new("L", (48, 48), color=0), (40, 40))
    report = evaluate_quality(
        _validated_image(overexposed_scene.convert("RGB")),
        _thresholds(min_laplacian_variance=0.0, min_tile_laplacian_variance=0.0),
    )
    brightness = _check(report, QualityCheckName.BRIGHTNESS)

    assert brightness.passed is False
    assert brightness.code is QualityReasonCode.IMAGE_TOO_BRIGHT


def test_equal_luminance_thresholds_pass_that_individual_check() -> None:
    """Using inclusive failure comparisons would make tuning boundaries unpredictable."""
    dark_boundary = evaluate_quality(
        _validated_image(Image.new("RGB", (64, 64), color=(25, 25, 25))), _thresholds()
    )
    bright_boundary = evaluate_quality(
        _validated_image(Image.new("RGB", (64, 64), color=(230, 230, 230))), _thresholds()
    )

    assert _check(dark_boundary, QualityCheckName.DARKNESS).passed is True
    assert _check(bright_boundary, QualityCheckName.BRIGHTNESS).passed is True


def test_multiple_quality_failures_are_preserved_in_one_report() -> None:
    """Short-circuiting at blur would hide the separately actionable darkness issue."""
    report = evaluate_quality(_validated_image(Image.new("RGB", (64, 64), color=(0, 0, 0))), _thresholds())

    assert report.passed is False
    assert report.reasons == (
        QualityReasonCode.IMAGE_TOO_BLURRY,
        QualityReasonCode.IMAGE_TOO_DARK,
    )
    assert len([check for check in report.checks if not check.passed]) == 2


def test_threshold_changes_change_blur_outcome_without_code_changes() -> None:
    """Hard-coding the blur cutoff would make deployment threshold tuning ineffective."""
    image = _validated_image(_checkerboard().filter(ImageFilter.GaussianBlur(radius=2)))
    permissive = evaluate_quality(
        image,
        _thresholds(
            min_laplacian_variance=1.0,
            min_tile_laplacian_variance=1.0,
            min_usable_sharp_tile_ratio=0.75,
        ),
    )
    strict = evaluate_quality(
        image,
        _thresholds(
            min_laplacian_variance=10_000.0,
            min_tile_laplacian_variance=10_000.0,
            min_usable_sharp_tile_ratio=0.75,
        ),
    )

    assert _check(permissive, QualityCheckName.BLUR).passed is True
    assert _check(strict, QualityCheckName.BLUR).passed is False
