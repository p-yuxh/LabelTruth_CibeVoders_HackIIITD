from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, JSON, Float, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class EvidenceLog(Base):
    """
    Evidence Log Table
    Caches product nutrition data, ingredient audit details, source URLs,
    and timestamps for transparency and fast query resolution.
    """
    __tablename__ = "evidence_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    query = Column(String(255), index=True, nullable=False)
    product_name = Column(String(255), index=True, nullable=True)
    brand = Column(String(255), nullable=True)
    category = Column(String(255), index=True, nullable=True)
    subcategory = Column(String(255), index=True, nullable=True)
    allergens = Column(JSON, default=list, nullable=True)
    may_contain_allergens = Column(JSON, default=list, nullable=True)
    data_completeness = Column(Float, default=1.0, nullable=True)
    
    # Structured normalized product data (nutrition, ingredients, claims, citations)
    product_data = Column(JSON, nullable=False)
    
    # List of verified source URLs crawled by TinyFish
    source_urls = Column(JSON, default=list, nullable=False)
    
    # Raw output from TinyFish (search, fetch, agent) for auditability
    raw_tinyfish_output = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    __table_args__ = (
        Index("ix_evidence_logs_category_subcategory", "category", "subcategory"),
        Index("ix_evidence_logs_allergens", "allergens"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "query": self.query,
            "product_name": self.product_name,
            "brand": self.brand,
            "category": self.category,
            "subcategory": self.subcategory,
            "allergens": self.allergens,
            "may_contain_allergens": self.may_contain_allergens,
            "data_completeness": self.data_completeness,
            "product_data": self.product_data,
            "source_urls": self.source_urls,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
