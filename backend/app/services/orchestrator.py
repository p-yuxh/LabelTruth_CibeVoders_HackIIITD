import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence_log import EvidenceLog
from app.services.tinyfish_scraper import TinyFishScraperService
from app.services.claims_auditor import LabelTruthClaimsAuditor
from app.services.personalized_scoring import PersonalizedScoringEngine
from app.services.reference_standards import ReferenceStandardsRegistry

logger = logging.getLogger("labeltruth.orchestrator")


class AuditOrchestrator:
    """
    Evidence-based Audit Orchestrator.
    Executes PostgreSQL evidence caching, TinyFish autonomous scraping,
    claim audits, statutory citations, and the Personalised Rating engine.
    """

    def __init__(
        self,
        scraper_service: Optional[TinyFishScraperService] = None,
        auditor_service: Optional[LabelTruthClaimsAuditor] = None,
    ):
        self.scraper = scraper_service or TinyFishScraperService()
        self.auditor = auditor_service or LabelTruthClaimsAuditor()
        self.scoring_engine = PersonalizedScoringEngine()

    async def audit_product(
        self,
        session: AsyncSession,
        query: str,
        force_refresh: bool = False,
        conditions: Optional[List[str]] = None,
        user_allergens: Optional[List[str]] = None,
        profile: str = "general_health",
        share_of_daily: float = 0.15,
        **kwargs
    ) -> Dict[str, Any]:
        cleaned_query = query.strip()
        normalized_query_key = cleaned_query.lower()

        selected_cond = conditions or ([profile] if profile else ["general_health"])

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
                product_data = dict(cached_entry.product_data)
                
                # Remove legacy score keys if present
                product_data.pop("claim_integrity_score", None)
                product_data.pop("legacy_score", None)

                # Personalised rating evaluation
                personalized_eval = self.scoring_engine.evaluate(
                    product_data=product_data,
                    selected_conditions=selected_cond,
                    user_allergens=user_allergens or [],
                )
                product_data["personalized_scoring"] = personalized_eval

                if not product_data.get("reference_standards"):
                    registry = ReferenceStandardsRegistry(default_share_of_daily=share_of_daily)
                    product_data["reference_standards"] = registry.get_all_citations_for_product(
                        product_data.get("front_pack_claims", []),
                        product_data.get("ingredients", [])
                    )

                # Fetch candidate category products from evidence log
                stmt_recs = select(EvidenceLog).order_by(EvidenceLog.created_at.desc()).limit(30)
                recs_res = await session.execute(stmt_recs)
                cached_recs = [r.product_data for r in recs_res.scalars().all() if r.product_data]
                product_data["recommendations"] = self.scoring_engine.rank_recommendations(
                    current_product=product_data,
                    candidate_products=cached_recs,
                    selected_conditions=selected_cond,
                    user_allergens=user_allergens or [],
                )

                return {
                    "query": cleaned_query,
                    "is_cached": True,
                    "evidence_log_id": cached_entry.id,
                    "created_at": cached_entry.created_at.isoformat() if cached_entry.created_at else datetime.now(timezone.utc).isoformat(),
                    "source_urls": cached_entry.source_urls or [],
                    "data": product_data,
                    "tinyfish_agent_raw": cached_entry.raw_tinyfish_output.get("agent_data") if cached_entry.raw_tinyfish_output else None,
                }

        logger.info(f"CACHE MISS for '{cleaned_query}'. Launching TinyFish web scraper & Claims Auditor.")

        # Step 2: Non-blocking Scraping Layer via TinyFish API
        tinyfish_result = await asyncio.to_thread(self.scraper.run_full_pipeline, cleaned_query)

        # Step 3: Data Normalization & Claims Audit Layer
        normalized_data = self.auditor.normalize_and_audit(
            query=cleaned_query,
            tinyfish_data=tinyfish_result,
            conditions=selected_cond,
            user_allergens=user_allergens or [],
            share_of_daily=share_of_daily,
        )

        normalized_data.pop("claim_integrity_score", None)
        normalized_data.pop("legacy_score", None)

        # Generate category recommendations
        stmt_recs = select(EvidenceLog).order_by(EvidenceLog.created_at.desc()).limit(30)
        recs_res = await session.execute(stmt_recs)
        cached_recs = [r.product_data for r in recs_res.scalars().all() if r.product_data]
        normalized_data["recommendations"] = self.scoring_engine.rank_recommendations(
            current_product=normalized_data,
            candidate_products=cached_recs,
            selected_conditions=selected_cond,
            user_allergens=user_allergens or [],
        )

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
            "created_at": evidence_log.created_at.isoformat() if evidence_log.created_at else datetime.now(timezone.utc).isoformat(),
            "source_urls": source_urls,
            "data": normalized_data,
            "tinyfish_agent_raw": tinyfish_result.get("agent_data"),
        }
