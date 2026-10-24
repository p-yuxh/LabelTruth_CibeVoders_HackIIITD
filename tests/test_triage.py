import asyncio
import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import (
    BarcodeResult,
    OCRResult,
    OCRTextBlock,
    VisionExtractionResult,
    ImageTriageResult,
)
from app.pipeline.triage import merge_image_signals, triage_images, PreprocessedImage
from app.pipeline.ocr import MockOCRProvider
from app.pipeline.vision import MockVisionProvider

client = TestClient(app)


def make_test_image_bytes(size=(200, 200), fmt="JPEG") -> bytes:
    im = Image.new("RGB", size, color="green")
    buf = io.BytesIO()
    im.save(buf, format=fmt)
    return buf.getvalue()


def test_merge_signals_with_front_and_ingredient_panel():
    # Image 1: Front photo with brand, name, variant, but no barcode or ingredients
    img1 = ImageTriageResult(
        image_index=1,
        barcode=None,
        ocr=OCRResult(blocks=[], full_text="", avg_confidence=0.0),
        vision=VisionExtractionResult(
            photo_type="front",
            brand="Oatly",
            product_name="Oat Drink",
            variant_or_flavour="Barista Edition",
            net_weight_or_volume="1 L",
            language="en",
            visible_ingredient_text=None,
            legibility=0.92,
        ),
    )

    # Image 2: Ingredient panel with legibility >= 0.7
    img2 = ImageTriageResult(
        image_index=2,
        barcode=BarcodeResult(code="7394376616037", format="EAN-13", valid_check_digit=True),
        ocr=OCRResult(
            blocks=[OCRTextBlock(text="Oat base, rapeseed oil, dipotassium phosphate", confidence=0.95)],
            full_text="Oat base, rapeseed oil, dipotassium phosphate",
            avg_confidence=0.95,
        ),
        vision=VisionExtractionResult(
            photo_type="ingredient_panel",
            brand="Oatly",
            product_name=None,
            variant_or_flavour=None,
            net_weight_or_volume=None,
            language="en",
            visible_ingredient_text="Oat base, rapeseed oil, dipotassium phosphate",
            legibility=0.88,
        ),
    )

    merged = merge_image_signals([img1, img2])

    assert merged.barcode == "7394376616037"
    assert merged.brand == "Oatly"
    assert merged.product_name == "Oat Drink"
    assert merged.variant_or_flavour == "Barista Edition"
    assert merged.net_weight_or_volume == "1 L"
    assert merged.language == "en"
    # Rule: If any image is an ingredient_panel or back photo with legibility >= 0.7, keep its OCR text as user_ocr_ingredients
    assert merged.user_ocr_ingredients == "Oat base, rapeseed oil, dipotassium phosphate"
    assert len(merged.images) == 2


def test_merge_signals_ignores_ingredient_panel_if_legibility_low():
    # Ingredient panel with low legibility (< 0.7)
    img_low_legibility = ImageTriageResult(
        image_index=1,
        barcode=None,
        ocr=OCRResult(
            blocks=[OCRTextBlock(text="Garbled text...", confidence=0.3)],
            full_text="Garbled text...",
            avg_confidence=0.3,
        ),
        vision=VisionExtractionResult(
            photo_type="ingredient_panel",
            brand=None,
            product_name=None,
            variant_or_flavour=None,
            net_weight_or_volume=None,
            language="en",
            visible_ingredient_text=None,
            legibility=0.45,  # < 0.70 threshold!
        ),
    )

    merged = merge_image_signals([img_low_legibility])

    # Should NOT keep low legibility OCR text
    assert merged.user_ocr_ingredients is None


def test_concurrent_triage_images():
    img_bytes = make_test_image_bytes()
    preprocessed = [
        PreprocessedImage(data=img_bytes, mime_type="image/jpeg", width=200, height=200, original_filename="front.jpg"),
        PreprocessedImage(data=img_bytes, mime_type="image/jpeg", width=200, height=200, original_filename="back.jpg"),
    ]

    mock_ocr = MockOCRProvider(
        OCRResult(
            blocks=[OCRTextBlock(text="Whole wheat flour, Water, Salt", confidence=0.91)],
            full_text="Whole wheat flour, Water, Salt",
            avg_confidence=0.91,
        )
    )
    mock_vision = MockVisionProvider(
        VisionExtractionResult(
            photo_type="ingredient_panel",
            brand="Organic Harvest",
            product_name="Whole Wheat Bread",
            variant_or_flavour="Multigrain",
            net_weight_or_volume="500g",
            language="en",
            visible_ingredient_text="Whole wheat flour, Water, Salt",
            legibility=0.85,
        )
    )

    merged = asyncio.run(triage_images(preprocessed, mock_ocr, mock_vision))

    assert merged.brand == "Organic Harvest"
    assert merged.product_name == "Whole Wheat Bread"
    assert merged.variant_or_flavour == "Multigrain"
    assert merged.net_weight_or_volume == "500g"
    assert merged.user_ocr_ingredients == "Whole wheat flour, Water, Salt"
    assert len(merged.images) == 2


def test_api_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["phase"] == 1


def test_api_analyze_single_image():
    img_data = make_test_image_bytes()
    files = [
        ("files", ("front.jpg", img_data, "image/jpeg"))
    ]
    response = client.post("/analyze", files=files)
    assert response.status_code == 200
    res_json = response.json()
    assert "barcode" in res_json
    assert "brand" in res_json
    assert "product_name" in res_json
    assert "variant_or_flavour" in res_json
    assert "user_ocr_ingredients" in res_json
    assert "images" in res_json
    assert len(res_json["images"]) == 1


def test_api_analyze_three_images():
    img_data1 = make_test_image_bytes(size=(300, 300), fmt="JPEG")
    img_data2 = make_test_image_bytes(size=(400, 400), fmt="PNG")
    img_data3 = make_test_image_bytes(size=(500, 500), fmt="JPEG")

    files = [
        ("files", ("front.jpg", img_data1, "image/jpeg")),
        ("files", ("back.png", img_data2, "image/png")),
        ("files", ("panel.jpg", img_data3, "image/jpeg")),
    ]
    response = client.post("/analyze", files=files)
    assert response.status_code == 200
    res_json = response.json()
    assert len(res_json["images"]) == 3


def test_api_analyze_rejects_more_than_three_images():
    img_data = make_test_image_bytes()
    files = [
        ("files", ("img1.jpg", img_data, "image/jpeg")),
        ("files", ("img2.jpg", img_data, "image/jpeg")),
        ("files", ("img3.jpg", img_data, "image/jpeg")),
        ("files", ("img4.jpg", img_data, "image/jpeg")),
    ]
    response = client.post("/analyze", files=files)
    assert response.status_code == 400
    assert "Exactly 1 to 3 images must be uploaded" in response.json()["detail"]


def test_api_analyze_rejects_zero_images():
    response = client.post("/analyze", files=[])
    assert response.status_code in (400, 422)


def test_api_analyze_rejects_invalid_file_type():
    # Test plain text upload
    files = [
        ("files", ("document.txt", b"Hello World text data", "text/plain"))
    ]
    response = client.post("/analyze", files=files)
    assert response.status_code == 400
    detail = response.json()["detail"].lower()
    assert "invalid" in detail or "corrupted" in detail

    # Test GIF format upload
    buf = io.BytesIO()
    im = Image.new("RGB", (100, 100), color="blue")
    im.save(buf, format="GIF")
    files_gif = [
        ("files", ("animated.gif", buf.getvalue(), "image/gif"))
    ]
    response_gif = client.post("/analyze", files=files_gif)
    assert response_gif.status_code == 400
    assert "unsupported format" in response_gif.json()["detail"].lower()
