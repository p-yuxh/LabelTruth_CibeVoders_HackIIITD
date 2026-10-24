"""SQLite SQLAlchemy cache keyed by barcode and normalized brand+product+variant."""
import logging
from typing import Optional
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Float
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings

logger = logging.getLogger("labeltruth.cache")

Base = declarative_base()


class ProductCache(Base):
    __tablename__ = "product_cache"

    cache_key = Column(String(255), primary_key=True, index=True)
    barcode = Column(String(50), index=True, nullable=True)
    normalized_name = Column(String(255), index=True, nullable=True)
    brand = Column(String(255), nullable=True)
    product_name = Column(String(255), nullable=True)
    variant = Column(String(255), nullable=True)
    size = Column(String(100), nullable=True)
    source_type = Column(String(50), nullable=True)
    source_url = Column(Text, nullable=True)
    ingredients_json = Column(Text, nullable=True)
    nutrition_json = Column(Text, nullable=True)
    raw_response_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_cache_db():
    """Create tables if they do not exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Initialized cache database.")

