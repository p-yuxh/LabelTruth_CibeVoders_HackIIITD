import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence_log import EvidenceLog
from app.services.tinyfish_scraper import TinyFishScraperService
from app.services.claims_auditor import LabelTruthClaimsAuditor

logger = logging.getLogger("labeltruth.orchestrator")


class AuditOrchestrator:
    """
    Central Orchestration Service
    Coordinates the pipeline:
    1. Check PostgreSQL Evidence Log cache
    2. On Cache Miss:
       a. Run TinyFish Scraping (Search -> Fetch -> Agent)
       b. Run LabelTruth Claims Auditor (deterministic schema normalization & claim verification)
       c. Persist result in PostgreSQL Evidence Log
    3. Return final result
    """

    def __init__(
        self,
        scraper_service: Optional[TinyFishScraperService] = None,
        auditor_service: Optional[LabelTruthClaimsAuditor] = None,
    ):
        self.scraper = scraper_service or TinyFishScraperService()
        self.auditor = auditor_service or LabelTruthClaimsAuditor()

    async def audit_product(
        self,
        session: AsyncSession,
        query: str,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        cleaned_query = query.strip()
        normalized_query_key = cleaned_query.lower()

        # Step 1: Cache check in PostgreSQL evidence log
        if not force_refresh:
            stmt = (
                select(EvidenceLog)
                .where(func.lower(EvidenceLog.query) == normalized_query_key)
                .order_by(EvidenceLog.created_at.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            cached_entry = result.scalar_one_or_none()

            if cached_entry:
                logger.info(f"CACHE HIT: Returning cached evidence log #{cached_entry.id} for '{cleaned_query}'")
                return {
                    "query": cleaned_query,
                    "is_cached": True,
                    "evidence_log_id": cached_entry.id,
                    "created_at": cached_entry.created_at.isoformat() if cached_entry.created_at else datetime.now(timezone.utc).isoformat(),
                    "source_urls": cached_entry.source_urls or [],
                    "data": cached_entry.product_data,
                    "tinyfish_agent_raw": cached_entry.raw_tinyfish_output.get("agent_data") if cached_entry.raw_tinyfish_output else None,
                }

        logger.info(f"CACHE MISS for '{cleaned_query}'. Launching TinyFish web scraper & Claims Auditor.")

        # Step 2: Sequential Scraping Layer via TinyFish API
        tinyfish_result = self.scraper.run_full_pipeline(cleaned_query)

        # Step 3: Data Normalization & Claims Audit Layer
        normalized_data = self.auditor.normalize_and_audit(cleaned_query, tinyfish_result)

        # Step 4: Persist to PostgreSQL Evidence Log
        product_name = normalized_data.get("product_name", {}).get("value")
        brand = normalized_data.get("brand", {}).get("value")
        source_urls = tinyfish_result.get("source_urls", [])

        evidence_log = EvidenceLog(
            query=cleaned_query,
            product_name=product_name,
            brand=brand,
            product_data=normalized_data,
            source_urls=source_urls,
            raw_tinyfish_output={
                "search_results": tinyfish_result.get("search_results", []),
                "agent_data": tinyfish_result.get("agent_data", {}),
            },
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        session.add(evidence_log)
        await session.commit()
        await session.refresh(evidence_log)

        logger.info(f"Successfully cached audit result in Evidence Log #{evidence_log.id} for '{cleaned_query}'")

        return {
            "query": cleaned_query,
            "is_cached": False,
            "evidence_log_id": evidence_log.id,
            "created_at": evidence_log.created_at.isoformat(),
            "source_urls": source_urls,
            "data": normalized_data,
            "tinyfish_agent_raw": tinyfish_result.get("agent_data"),
        }
