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
    claim audits, statutory citations, and the revised Personalized Rating
    and Match Score engine.
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
        preferences: Optional[List[str]] = None,
        avoided_ingredients: Optional[List[str]] = None,
        preferred_ingredients: Optional[List[str]] = None,
        profile: str = "general_health",
        strict_palm_oil: bool = False,
        goals: Optional[list] = None,
        share_of_daily: float = 0.15,
    ) -> Dict[str, Any]:
        cleaned_query = query.strip()
        normalized_query_key = cleaned_query.lower()

        # Normalize conditions and preferences
        selected_cond = conditions or ([profile] if profile else ["general_health"])
        user_pref = list(preferences or [])
        if strict_palm_oil and "avoid_palm_oil" not in user_pref:
            user_pref.append("avoid_palm_oil")
        if goals:
            user_pref.extend(goals)

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
                
                # Remove legacy claim_integrity_score if present in cache
                product_data.pop("claim_integrity_score", None)

                # Dynamic personalization on cache hit
                personalized_eval = self.scoring_engine.evaluate(
                    product_data=product_data,
                    selected_conditions=selected_cond,
                    user_allergens=user_allergens or [],
                    preferences=user_pref,
                    avoided_ingredients=avoided_ingredients or [],
                    preferred_ingredients=preferred_ingredients or [],
                )
                product_data["personalized_scoring"] = personalized_eval

                if not product_data.get("reference_standards"):
                    registry = ReferenceStandardsRegistry(default_share_of_daily=share_of_daily)
                    product_data["reference_standards"] = registry.get_all_citations_for_product(
                        product_data.get("front_pack_claims", []),
                        product_data.get("ingredients", [])
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

        # Step 2: Sequential Scraping Layer via TinyFish API
        tinyfish_result = self.scraper.run_full_pipeline(cleaned_query)

        # Step 3: Data Normalization & Claims Audit Layer
        normalized_data = self.auditor.normalize_and_audit(
            query=cleaned_query,
            tinyfish_data=tinyfish_result,
            conditions=selected_cond,
            user_allergens=user_allergens or [],
            preferences=user_pref,
            avoided_ingredients=avoided_ingredients or [],
            preferred_ingredients=preferred_ingredients or [],
            share_of_daily=share_of_daily,
        )

        # Remove legacy claim_integrity_score if present
        normalized_data.pop("claim_integrity_score", None)

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
