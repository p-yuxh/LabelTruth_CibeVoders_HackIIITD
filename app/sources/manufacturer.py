"""Manufacturer site retriever using Tavily and Trafilatura."""
import logging
from typing import List, Optional
from app.sources import ProductSource
from app.schemas import CandidateProduct

logger = logging.getLogger("labeltruth.sources.manufacturer")


class ManufacturerSource(ProductSource):
    """Searches official manufacturer domains via Tavily and extracts label content."""

    async def search(self, query: str) -> List[CandidateProduct]:
        return []

    async def get_by_barcode(self, barcode: str) -> Optional[CandidateProduct]:
        return None

