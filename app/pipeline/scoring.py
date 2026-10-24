"""Match scoring pipeline module (Phase 2)."""
import logging
from typing import List, Tuple
from rapidfuzz import fuzz

from app.schemas import CandidateProduct
from app.config import settings

logger = logging.getLogger("labeltruth.scoring")


class MatchScorer:
    """Scores candidate products against extracted signals using RapidFuzz."""

    def __init__(
        self,
        confident_threshold: float = None,
        ambiguous_threshold: float = None,
    ):
        self.confident_threshold = confident_threshold or settings.confident_threshold
        self.ambiguous_threshold = ambiguous_threshold or settings.ambiguous_threshold

    def score_candidate(
        self,
        candidate: CandidateProduct,
        target_brand: str = None,
        target_name: str = None,
        target_variant: str = None,
        target_size: str = None,
        has_barcode_match: bool = False,
    ) -> float:
        """Placeholder for Phase 2 weighted RapidFuzz matching."""
        if has_barcode_match:
            return 1.0
        return 0.0

