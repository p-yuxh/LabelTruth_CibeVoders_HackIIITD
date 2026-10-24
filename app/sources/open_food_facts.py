"""Open Food Facts API v2 client source."""
import logging
from typing import List, Optional
from app.sources import ProductSource
from app.schemas import CandidateProduct

logger = logging.getLogger("labeltruth.sources.openfoodfacts")


class OpenFoodFactsSource(ProductSource):
    """Fetches product details from Open Food Facts API v2."""

    def __init__(self, base_url: str = "https://world.openfoodfacts.org"):
        self.base_url = base_url

    async def get_by_barcode(self, barcode: str) -> Optional[CandidateProduct]:
        """Fetch candidate from Open Food Facts by barcode."""
        return None

    async def search(self, query: str) -> List[CandidateProduct]:
        """Search products in Open Food Facts."""
        return []

