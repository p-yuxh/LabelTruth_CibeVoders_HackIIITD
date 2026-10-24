import asyncio
import io
import logging
import time
from typing import List, Optional, Tuple
from PIL import Image, ImageOps
from fastapi import HTTPException, status

from app.config import settings
from app.schemas import (
    BarcodeResult,
    OCRResult,
    VisionExtractionResult,
    ImageTriageResult,
    MergedSignals,
)
from app.pipeline.barcode import decode_barcode_bytes
from app.pipeline.ocr import OCRProvider
from app.pipeline.vision import VisionProvider

logger = logging.getLogger("labeltruth.triage")


class PreprocessedImage:
    """Holds processed and sanitized image data."""

    def __init__(self, data: bytes, mime_type: str, width: int, height: int, original_filename: str):
        self.data = data
        self.mime_type = mime_type
        self.width = width
        self.height = height
        self.original_filename = original_filename


def validate_and_preprocess_image(
    raw_bytes: bytes,
    filename: Optional[str] = None,
    content_type: Optional[str] = None,
) -> PreprocessedImage:
    """
    Validate image file size (max 8MB), format (PNG/JPG),
    resize large images (max side 2000px), and strip EXIF metadata.
    """
    fname = filename or "image.jpg"

    # 1. Validate file size
    if len(raw_bytes) > settings.max_image_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image '{fname}' size ({len(raw_bytes)} bytes) exceeds the maximum allowed 8 MB limit.",
        )

    # 2. Open and validate format via PIL
    try:
        img = Image.open(io.BytesIO(raw_bytes))
        img_format = (img.format or "").upper()
        if img_format not in ("JPEG", "JPG", "PNG"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Image '{fname}' has unsupported format '{img_format}'. Only PNG and JPG/JPEG are permitted.",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read image '{fname}': Invalid or corrupted image data. Error: {str(e)}",
        )

    # 3. Orient image according to EXIF tags before stripping EXIF
    try:
        img = ImageOps.exif_transpose(img)
    except Exception as e:
        logger.debug(f"exif_transpose skipped on '{fname}': {e}")

    # 4. Resize if max side > 2000 px
    w, h = img.size
    max_side = settings.max_image_side_px
    if max(w, h) > max_side:
        ratio = max_side / float(max(w, h))
        new_w = max(1, int(w * ratio))
        new_h = max(1, int(h * ratio))
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        logger.info(f"Resized image '{fname}' from ({w}, {h}) to ({new_w}, {new_h})")
        w, h = new_w, new_h

    # 5. Strip EXIF by saving to a clean buffer without metadata
    buffer = io.BytesIO()
    if img_format in ("JPEG", "JPG"):
        out_mime = "image/jpeg"
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.save(buffer, format="JPEG", quality=90)
    else:
        out_mime = "image/png"
        img.save(buffer, format="PNG")

    processed_bytes = buffer.getvalue()
    return PreprocessedImage(
        data=processed_bytes,
        mime_type=out_mime,
        width=w,
        height=h,
        original_filename=fname,
    )


async def triage_single_image(
    image: PreprocessedImage,
    image_index: int,
    ocr_provider: OCRProvider,
    vision_provider: VisionProvider,
) -> ImageTriageResult:
    """
    Run barcode decoding, OCR extraction, and vision extraction concurrently for a single image.
    Log timing for each step without exposing credentials.
    """
    logger.info(f"[Image {image_index}] Starting concurrent triage for '{image.original_filename}'")
    start_total = time.perf_counter()

    async def _run_barcode() -> Optional[BarcodeResult]:
        t0 = time.perf_counter()
        res = await asyncio.to_thread(decode_barcode_bytes, image.data)
        elapsed = time.perf_counter() - t0
        found_str = f"Found '{res.code}' ({res.format})" if res else "None"
        logger.info(f"[Image {image_index}] Barcode step finished in {elapsed:.3f}s. Result: {found_str}")
        return res

    async def _run_ocr() -> OCRResult:
        t0 = time.perf_counter()
        res = await ocr_provider.extract_text(image.data)
        elapsed = time.perf_counter() - t0
        preview = res.full_text[:40] + "..." if len(res.full_text) > 40 else res.full_text
        logger.info(f"[Image {image_index}] OCR step finished in {elapsed:.3f}s ({len(res.blocks)} blocks). Text: '{preview}'")
        return res

    async def _run_vision() -> VisionExtractionResult:
        t0 = time.perf_counter()
        res = await vision_provider.extract_product_info(image.data, mime_type=image.mime_type)
        elapsed = time.perf_counter() - t0
        logger.info(
            f"[Image {image_index}] Vision step finished in {elapsed:.3f}s. "
            f"Type: '{res.photo_type}', Brand: '{res.brand}', Name: '{res.product_name}', Legibility: {res.legibility:.2f}"
        )
        return res

    barcode_res, ocr_res, vision_res = await asyncio.gather(
        _run_barcode(),
        _run_ocr(),
        _run_vision(),
    )

    total_elapsed = time.perf_counter() - start_total
    logger.info(f"[Image {image_index}] Full triage completed in {total_elapsed:.3f}s")

    return ImageTriageResult(
        image_index=image_index,
        barcode=barcode_res,
        ocr=ocr_res,
        vision=vision_res,
    )


def merge_image_signals(triage_results: List[ImageTriageResult]) -> MergedSignals:
    """
    Merge signals across all triaged images:
    - Barcode: first valid decoded barcode.
    - Brand, Product Name, Variant, Size: prefer front photo and highest legibility score.
    - user_ocr_ingredients: If any image is an ingredient_panel or back photo with legibility >= 0.7,
      keep its OCR text as user_ocr_ingredients.
    """
    merged_barcode: Optional[str] = None
    best_brand: Optional[str] = None
    best_name: Optional[str] = None
    best_variant: Optional[str] = None
    best_size: Optional[str] = None
    best_lang: Optional[str] = None

    # Track legibility scores for selection
    brand_score = -1.0
    name_score = -1.0
    variant_score = -1.0
    size_score = -1.0
    lang_score = -1.0

    eligible_ingredient_texts: List[Tuple[float, str]] = []

    for item in triage_results:
        # 1. Barcode
        if not merged_barcode and item.barcode and item.barcode.valid_check_digit:
            merged_barcode = item.barcode.code

        v = item.vision
        # Front photos get a priority boost for product identification
        priority_multiplier = 1.2 if v.photo_type == "front" else 1.0
        effective_score = v.legibility * priority_multiplier

        # 2. Brand
        if v.brand and effective_score > brand_score:
            best_brand = v.brand.strip()
            brand_score = effective_score

        # 3. Product Name
        if v.product_name and effective_score > name_score:
            best_name = v.product_name.strip()
            name_score = effective_score

        # 4. Variant / Flavour
        if v.variant_or_flavour and effective_score > variant_score:
            best_variant = v.variant_or_flavour.strip()
            variant_score = effective_score

        # 5. Net weight or volume
        if v.net_weight_or_volume and v.legibility > size_score:
            best_size = v.net_weight_or_volume.strip()
            size_score = v.legibility

        # 6. Language
        if v.language and v.legibility > lang_score:
            best_lang = v.language.strip()
            lang_score = v.legibility

        # 7. Check user OCR ingredients rule:
        # "If any image is an ingredient_panel or back photo with legibility >= 0.7, keep its OCR text as user_ocr_ingredients."
        if v.photo_type in ("ingredient_panel", "back") and v.legibility >= 0.70:
            # Use OCR full_text if present, or fall back to visible_ingredient_text from vision
            candidate_text = item.ocr.full_text.strip()
            if not candidate_text and v.visible_ingredient_text:
                candidate_text = v.visible_ingredient_text.strip()
            if candidate_text:
                eligible_ingredient_texts.append((v.legibility, candidate_text))

    user_ocr_ingredients: Optional[str] = None
    if eligible_ingredient_texts:
        # Sort by legibility descending and select highest quality
        eligible_ingredient_texts.sort(key=lambda x: x[0], reverse=True)
        user_ocr_ingredients = eligible_ingredient_texts[0][1]

    return MergedSignals(
        barcode=merged_barcode,
        brand=best_brand,
        product_name=best_name,
        variant_or_flavour=best_variant,
        net_weight_or_volume=best_size,
        language=best_lang,
        user_ocr_ingredients=user_ocr_ingredients,
        images=triage_results,
    )


async def triage_images(
    images: List[PreprocessedImage],
    ocr_provider: OCRProvider,
    vision_provider: VisionProvider,
) -> MergedSignals:
    """Concurrently triage 1 to 3 preprocessed images and merge their signals."""
    t0 = time.perf_counter()
    logger.info(f"Executing concurrent triage across {len(images)} image(s)...")

    tasks = [
        triage_single_image(
            image=img,
            image_index=idx + 1,
            ocr_provider=ocr_provider,
            vision_provider=vision_provider,
        )
        for idx, img in enumerate(images)
    ]

    triage_results = await asyncio.gather(*tasks)
    merged = merge_image_signals(triage_results)

    elapsed = time.perf_counter() - t0
    logger.info(f"Overall triage and signal merge completed in {elapsed:.3f}s")
    return merged

