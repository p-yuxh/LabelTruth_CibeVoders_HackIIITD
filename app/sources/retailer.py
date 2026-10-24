"""Retailer product source."""
import logging
from typing import List, Optional
from app.sources import ProductSource
from app.schemas import CandidateProduct

logger = logging.getLogger("labeltruth.sources.retailer")


class RetailerSource(ProductSource):
    """Fallback source from verified retailer pages."""

    async def search(self, query: str) -> List[CandidateProduct]:
        return []

    async def get_by_barcode(self, barcode: str) -> Optional[CandidateProduct]:
        return None

