import abc
import asyncio
import json
import logging
import re
from typing import Optional

from pydantic import ValidationError

from app.schemas import VisionExtractionResult
from app.config import settings

logger = logging.getLogger("labeltruth.vision")

VISION_PROMPT = """Analyze this packaged food product photo carefully.
Your task is to identify and extract the product details into a strict JSON object.

Extract the following fields:
- photo_type: Exactly one of ["front", "back", "barcode", "ingredient_panel", "other"].
  * "front": front display panel of the package showing the brand/product name.
  * "back": back of the pack typically showing information panels.
  * "barcode": close-up shot focused specifically on a barcode.
  * "ingredient_panel": close-up or clear view of the ingredients list / nutrition box.
  * "other": anything else.
- brand: The brand or manufacturer name (e.g., "Lay's", "Cadbury", "Nestle", "Amul"), or null if not visible.
- product_name: The specific product title (e.g., "Potato Chips", "Bournvita", "Maggi 2-Minute Noodles"), or null if not visible.
- variant_or_flavour: The flavor, variant, or edition (e.g., "Magic Masala", "Cream & Onion", "Dark Chocolate", "Zero Sugar"), or null if not visible.
- net_weight_or_volume: Net weight or quantity as printed (e.g., "50 g", "400 g", "1 L"), or null if not visible.
- language: Primary language code (e.g., "en", "hi", "es"), or null.
- visible_ingredient_text: Verbatim raw text of the ingredient list if visible in this photo, otherwise null.
- legibility: A score between 0.0 (unreadable, blurry) and 1.0 (crystal clear text).

Output ONLY valid JSON matching this schema. Do not include markdown codeblocks or extra prose.
"""


class VisionProvider(abc.ABC):
    """Abstract Base Class for Vision Providers."""

    @abc.abstractmethod
    async def extract_product_info(
        self,
        image_bytes: bytes,
        mime_type: str = "image/jpeg"
    ) -> VisionExtractionResult:
        """Analyze image bytes and return structured, Pydantic-validated product details."""
        pass


class GeminiVisionProvider(VisionProvider):
    """
    Gemini Vision Provider using the official google-genai SDK.
    Model name is dynamically retrieved from config (settings.gemini_model).
    """

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or settings.gemini_api_key
        self.model_name = model_name or settings.gemini_model or "gemini-2.5-flash"
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY is not configured in settings or environment.")
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    async def extract_product_info(
        self,
        image_bytes: bytes,
        mime_type: str = "image/jpeg"
    ) -> VisionExtractionResult:
        from google.genai import types

        client = self._get_client()

        image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        contents = [image_part, VISION_PROMPT]

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=VisionExtractionResult,
            temperature=0.1,
        )

        max_retries = 3
        backoff = 1.0

        for attempt in range(1, max_retries + 1):
            try:
                response = await client.aio.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=config,
                )

                raw_text = response.text or ""
                # Strip markdown fences if present
                clean_text = raw_text.strip()
                if clean_text.startswith("```"):
                    clean_text = re.sub(r"^```(?:json)?", "", clean_text)
                    clean_text = re.sub(r"```$", "", clean_text).strip()

                parsed_json = json.loads(clean_text)
                return VisionExtractionResult.model_validate(parsed_json)

            except ValidationError as ve:
                logger.error(f"Gemini output failed Pydantic validation: {ve}")
                raise
            except Exception as exc:
                if attempt == max_retries:
                    logger.error(f"Gemini vision call failed after {attempt} attempts: {exc}")
                    raise
                logger.warning(f"Gemini call attempt {attempt} failed ({exc}), retrying in {backoff:.1f}s...")
                await asyncio.sleep(backoff)
                backoff *= 2.0


class MockVisionProvider(VisionProvider):
    """Mock vision provider for unit tests and offline testing."""

    def __init__(self, predefined_result: Optional[VisionExtractionResult] = None):
        self.predefined_result = predefined_result or VisionExtractionResult(
            photo_type="front",
            brand="MockBrand",
            product_name="Crunchy Granola",
            variant_or_flavour="Honey Almond",
            net_weight_or_volume="400g",
            language="en",
            visible_ingredient_text=None,
            legibility=0.95
        )

    async def extract_product_info(
        self,
        image_bytes: bytes,
        mime_type: str = "image/jpeg"
    ) -> VisionExtractionResult:
        return self.predefined_result


def get_vision_provider(provider_type: Optional[str] = None) -> VisionProvider:
    """Factory to retrieve configured VisionProvider instance."""
    p_type = (provider_type or settings.vision_provider or "gemini").lower()
    if p_type == "mock":
        return MockVisionProvider()
    elif p_type == "gemini":
        if not settings.gemini_api_key:
            logger.info("GEMINI_API_KEY not configured; using MockVisionProvider for development.")
            return MockVisionProvider()
        return GeminiVisionProvider()
    else:
        logger.warning(f"Unknown Vision provider '{p_type}'; falling back to MockVisionProvider.")
        return MockVisionProvider()

