import logging
from typing import List

from app.config import settings
from app.schemas import MergedSignals
from app.pipeline.ocr import get_ocr_provider, OCRProvider
from app.pipeline.vision import get_vision_provider, VisionProvider
from app.pipeline.triage import PreprocessedImage, triage_images

logger = logging.getLogger("labeltruth.orchestrator")


class PipelineOrchestrator:
    """
    Coordinates the multi-stage food product analysis pipeline.
    Phase 1: Concurrent triage and signal extraction.
    Phases 2-4: Candidate lookup, match scoring, retrieval, verification, and normalization.
    """

    def __init__(
        self,
        ocr_provider: OCRProvider = None,
        vision_provider: VisionProvider = None,
    ):
        self.ocr_provider = ocr_provider or get_ocr_provider()
        self.vision_provider = vision_provider or get_vision_provider()

    async def analyze_images(self, images: List[PreprocessedImage]) -> MergedSignals:
        """Execute Phase 1 signal extraction across 1-3 images."""
        logger.info(f"Orchestrator starting analysis for {len(images)} image(s)")
        merged_signals = await triage_images(
            images=images,
            ocr_provider=self.ocr_provider,
            vision_provider=self.vision_provider,
        )
        return merged_signals

