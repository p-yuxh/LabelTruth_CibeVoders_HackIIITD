import abc
import asyncio
import io
import logging
from typing import List, Optional
import numpy as np
from PIL import Image

from app.schemas import OCRResult, OCRTextBlock
from app.config import settings

logger = logging.getLogger("labeltruth.ocr")


class OCRProvider(abc.ABC):
    """Abstract Base Class for OCR providers."""

    @abc.abstractmethod
    async def extract_text(self, image_bytes: bytes) -> OCRResult:
        """Extract text blocks with confidence scores from raw image bytes."""
        pass


class PaddleOCRProvider(OCRProvider):
    """
    PaddleOCR implementation for multilingual text extraction.
    Lazy-loads PaddleOCR engine to avoid startup penalties.
    """

    def __init__(self, lang: str = "en", use_angle_cls: bool = True):
        self.lang = lang
        self.use_angle_cls = use_angle_cls
        self._ocr = None
        self._load_lock = asyncio.Lock()

    def _get_engine(self):
        if self._ocr is None:
            try:
                from paddleocr import PaddleOCR
                self._ocr = PaddleOCR(use_angle_cls=self.use_angle_cls, lang=self.lang, show_log=False)
            except Exception as e:
                logger.warning(f"PaddleOCR failed to initialize: {e}. OCR will return empty result unless mock is used.")
                raise
        return self._ocr

    def _sync_ocr(self, img_array: np.ndarray) -> OCRResult:
        engine = self._get_engine()
        result = engine.ocr(img_array, cls=self.use_angle_cls)

        blocks: List[OCRTextBlock] = []
        if not result or result[0] is None:
            return OCRResult(blocks=[], full_text="", avg_confidence=0.0)

        total_conf = 0.0
        for line in result[0]:
            # line structure: [bbox_coords, (text, confidence)]
            if len(line) >= 2:
                bbox_points, (text, conf) = line[0], line[1]
                conf = float(conf)
                blocks.append(OCRTextBlock(
                    text=text.strip(),
                    confidence=max(0.0, min(1.0, conf)),
                    bbox=bbox_points
                ))
                total_conf += conf

        full_text = " ".join(b.text for b in blocks if b.text)
        avg_conf = total_conf / len(blocks) if blocks else 0.0

        return OCRResult(
            blocks=blocks,
            full_text=full_text,
            avg_confidence=round(avg_conf, 4)
        )

    async def extract_text(self, image_bytes: bytes) -> OCRResult:
        try:
            # Convert bytes to numpy array
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img_arr = np.array(image)
            return await asyncio.to_thread(self._sync_ocr, img_arr)
        except Exception as exc:
            logger.warning(f"PaddleOCR processing error: {exc}")
            return OCRResult(blocks=[], full_text="", avg_confidence=0.0)


class MockOCRProvider(OCRProvider):
    """Mock OCR provider for unit tests and local development."""

    def __init__(self, mock_result: Optional[OCRResult] = None):
        self.mock_result = mock_result or OCRResult(
            blocks=[
                OCRTextBlock(text="Sample Ingredients: Oats, Sugar, Cocoa", confidence=0.92),
                OCRTextBlock(text="Net Wt: 400g", confidence=0.88),
            ],
            full_text="Sample Ingredients: Oats, Sugar, Cocoa Net Wt: 400g",
            avg_confidence=0.90
        )

    async def extract_text(self, image_bytes: bytes) -> OCRResult:
        return self.mock_result


def get_ocr_provider(provider_type: Optional[str] = None) -> OCRProvider:
    """Factory to instantiate the appropriate OCR provider."""
    p_type = (provider_type or settings.ocr_provider or "paddleocr").lower()
    if p_type == "mock":
        return MockOCRProvider()
    elif p_type == "paddleocr":
        try:
            import paddleocr  # check if module is present
            return PaddleOCRProvider()
        except ImportError:
            logger.info("PaddleOCR library not installed; falling back to MockOCRProvider for local execution.")
            return MockOCRProvider()
    else:
        logger.warning(f"Unknown OCR provider '{p_type}'; falling back to MockOCRProvider.")
        return MockOCRProvider()

