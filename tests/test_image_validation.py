import io
import pytest
from PIL import Image
from PIL.ExifTags import TAGS
from fastapi import HTTPException

from app.pipeline.triage import validate_and_preprocess_image


def create_test_image(
    size=(800, 600),
    fmt="JPEG",
    color="blue",
    add_exif=False,
) -> bytes:
    """Helper to generate in-memory test images."""
    im = Image.new("RGB", size, color=color)
    buf = io.BytesIO()

    if add_exif:
        exif = im.getexif()
        # Tag 271: Make, Tag 305: Software
        exif[271] = "LabelTruthCam"
        exif[305] = "LabelTruth Test Suite"
        im.save(buf, format=fmt, exif=exif)
    else:
        im.save(buf, format=fmt)

    return buf.getvalue()


def test_valid_jpeg_acceptance():
    data = create_test_image(size=(800, 600), fmt="JPEG")
    processed = validate_and_preprocess_image(data, filename="pack_front.jpg")

    assert processed.mime_type == "image/jpeg"
    assert processed.width == 800
    assert processed.height == 600
    assert len(processed.data) > 0


def test_valid_png_acceptance():
    data = create_test_image(size=(640, 480), fmt="PNG")
    processed = validate_and_preprocess_image(data, filename="pack_back.png")

    assert processed.mime_type == "image/png"
    assert processed.width == 640
    assert processed.height == 480
    assert len(processed.data) > 0


def test_large_dimension_image_resizing():
    # 3000 x 1500 (aspect ratio 2:1)
    data = create_test_image(size=(3000, 1500), fmt="JPEG")
    processed = validate_and_preprocess_image(data, filename="large_photo.jpg")

    # Max side should be capped at 2000px, aspect ratio preserved
    assert processed.width == 2000
    assert processed.height == 1000

    # Verify actual image data size
    result_im = Image.open(io.BytesIO(processed.data))
    assert result_im.size == (2000, 1000)


def test_large_vertical_dimension_image_resizing():
    # 1200 x 3600 (aspect ratio 1:3)
    data = create_test_image(size=(1200, 3600), fmt="JPEG")
    processed = validate_and_preprocess_image(data, filename="tall_photo.jpg")

    assert processed.height == 2000
    assert processed.width == 666


def test_exif_metadata_stripping():
    # Generate image with EXIF metadata
    data = create_test_image(size=(500, 500), fmt="JPEG", add_exif=True)

    # Verify original has EXIF
    original_im = Image.open(io.BytesIO(data))
    orig_exif = original_im.getexif()
    assert bool(orig_exif) is True
    assert 271 in orig_exif  # Make

    # Preprocess image
    processed = validate_and_preprocess_image(data, filename="photo_with_exif.jpg")

    # Verify output has NO EXIF tags
    processed_im = Image.open(io.BytesIO(processed.data))
    clean_exif = processed_im.getexif()
    assert bool(clean_exif) is False


def test_image_size_exceeding_8mb_rejection():
    # Generate dummy bytes > 8 MB (8 * 1024 * 1024 + 10)
    oversized_data = b"0" * (8 * 1024 * 1024 + 100)

    with pytest.raises(HTTPException) as exc_info:
        validate_and_preprocess_image(oversized_data, filename="giant.jpg")

    assert exc_info.value.status_code == 400
    assert "exceeds the maximum allowed 8 MB limit" in exc_info.value.detail


def test_unsupported_format_gif_rejection():
    buf = io.BytesIO()
    im = Image.new("RGB", (100, 100), color="red")
    im.save(buf, format="GIF")
    gif_data = buf.getvalue()

    with pytest.raises(HTTPException) as exc_info:
        validate_and_preprocess_image(gif_data, filename="animated.gif")

    assert exc_info.value.status_code == 400
    assert "unsupported format" in exc_info.value.detail


def test_corrupted_image_rejection():
    corrupted_data = b"NOT_AN_IMAGE_DATA_12345"

    with pytest.raises(HTTPException) as exc_info:
        validate_and_preprocess_image(corrupted_data, filename="corrupted.png")

    assert exc_info.value.status_code == 400
    assert "Invalid or corrupted image data" in exc_info.value.detail

