"""Product data source providers."""
import abc
from typing import List, Optional
from app.schemas import CandidateProduct


class ProductSource(abc.ABC):
    """Abstract interface for swappable product data sources."""

    @abc.abstractmethod
    async def search(self, query: str) -> List[CandidateProduct]:
        """Search products by name or query string."""
        pass

    @abc.abstractmethod
    async def get_by_barcode(self, barcode: str) -> Optional[CandidateProduct]:
        """Fetch exact product by barcode."""
        pass

