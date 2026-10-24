import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.evidence_log import EvidenceLog
from app.schemas.product import (
    AuditRequest,
    AuditResponse,
    EvidenceLogItem,
    PersonalizeRequest,
)
from app.services.orchestrator import AuditOrchestrator
from app.services.image_detector import ProductImageDetector
from app.services.personalized_scoring import PersonalizedScoringEngine
from app.services.reference_standards import (
    ReferenceStandardsRegistry,
    FSSAI_CLAIM_RULES,
    ICMR_NIN_DAILY_LIMITS,
    DIABETES_CLINICAL_GUIDANCE,
    GLOBAL_REFERENCES,
    THIRD_PARTY_LAB_FRAMEWORK,
)
from app.config import settings

logger = logging.getLogger("labeltruth.api")
router = APIRouter()
orchestrator = AuditOrchestrator()
image_detector = ProductImageDetector()
scoring_engine = PersonalizedScoringEngine()
standards_registry = ReferenceStandardsRegistry()


@router.post(
    "/audit",
    response_model=AuditResponse,
    summary="Audit Packaged Food Claims & Nutrition",
    description="Query PostgreSQL evidence log cache first; if cache miss, scrape via TinyFish API and normalize with Claude API."
)
async def audit_product(
    request: AuditRequest,
    db: AsyncSession = Depends(get_db),
):
    clean_q = request.query.strip().lower()
    if clean_q in ["packaged food product", "packaged food", "food", "product", "packaged"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Please specify a specific packaged food brand or product name (e.g. Lay's Potato Chips, Cadbury Bournvita, Maggi Noodles).",
        )

    try:
        result = await orchestrator.audit_product(
            session=db,
            query=request.query,
            force_refresh=request.force_refresh,
            profile=request.profile or "general_health",
            strict_palm_oil=bool(request.strict_palm_oil),
            goals=request.goals or [],
            share_of_daily=request.share_of_daily if request.share_of_daily is not None else 0.15,
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"Error executing audit for query '{request.query}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audit failed: {str(exc)}",
        )


@router.post(
    "/detect-image",
    summary="Detect Product from Packaging Image",
    description="Accepts an uploaded image file of product packaging and extracts the identified product name using OCR & brand matching."
)
async def detect_image(
    file: UploadFile = File(..., description="Image file of the food product packaging (JPEG, PNG, WEBP)"),
):
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        
        detection_result = image_detector.detect_product_from_bytes(content, filename=file.filename)
        return detection_result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        logger.exception(f"Image detection error: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to process image: {str(exc)}")


@router.post(
    "/audit-image",
    response_model=AuditResponse,
    summary="Direct Product Audit from Packaging Image",
    description="Upload an image of a food package to automatically detect the product and execute the full claims audit."
)
async def audit_image(
    file: UploadFile = File(..., description="Image file of the food product packaging"),
    force_refresh: bool = Form(False, description="Bypass cache and force fresh web extraction"),
    db: AsyncSession = Depends(get_db),
):
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        
        detection_result = image_detector.detect_product_from_bytes(content, filename=file.filename)
        product_query = detection_result.get("detected_product", "").strip()
        
        if not product_query or product_query.lower() in ["packaged food product", "packaged food", "food", "product"]:
            raise HTTPException(
                status_code=422, 
                detail="Could not clearly identify a brand or product name from the image. Please try a clearer photo or enter the name manually."
            )
        
        logger.info(f"Image auto-detected product '{product_query}'. Running audit...")
        result = await orchestrator.audit_product(
            session=db,
            query=product_query,
            force_refresh=force_refresh,
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"Direct image audit error: {exc}")
        raise HTTPException(status_code=500, detail=f"Image audit failed: {str(exc)}")


@router.get(
    "/evidence-logs",
    response_model=List[EvidenceLogItem],
    summary="List Cached Evidence Logs",
    description="Retrieve cached audit records stored in the PostgreSQL database."
)
async def list_evidence_logs(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(EvidenceLog)
        .order_by(desc(EvidenceLog.created_at))
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    records = result.scalars().all()
    return [
        EvidenceLogItem(
            id=r.id,
            query=r.query,
            product_name=r.product_name,
            brand=r.brand,
            source_urls=r.source_urls or [],
            created_at=r.created_at.isoformat() if r.created_at else "",
            updated_at=r.updated_at.isoformat() if r.updated_at else "",
            product_data=r.product_data or {},
        )
        for r in records
    ]


@router.get(
    "/evidence-logs/{log_id}",
    response_model=EvidenceLogItem,
    summary="Get Specific Evidence Log by ID"
)
async def get_evidence_log(
    log_id: int,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(EvidenceLog).where(EvidenceLog.id == log_id)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence log #{log_id} not found",
        )
    return EvidenceLogItem(
        id=record.id,
        query=record.query,
        product_name=record.product_name,
        brand=record.brand,
        source_urls=record.source_urls or [],
        created_at=record.created_at.isoformat() if record.created_at else "",
        updated_at=record.updated_at.isoformat() if record.updated_at else "",
        product_data=record.product_data or {},
    )


@router.post(
    "/score-personal",
    summary="Instant Personalized Score Calculation",
    description="Calculates profile suitability (0-100), preference match (0-100), and personal match score (75/25) for any product payload with hard exclusion checks."
)
async def score_personal(request: PersonalizeRequest):
    engine = PersonalizedScoringEngine(share_of_daily=request.share_of_daily)
    score_result = engine.evaluate_personalized_fit(
        product_data=request.product_data,
        profile_key=request.profile,
        strict_palm_oil_avoidance=request.strict_palm_oil,
        preferred_goals=request.goals,
        share_of_daily=request.share_of_daily
    )
    all_profiles = engine.evaluate_all_three_profiles(
        product_data=request.product_data,
        strict_palm_oil_avoidance=request.strict_palm_oil,
        preferred_goals=request.goals,
        share_of_daily=request.share_of_daily
    )
    score_result["all_profiles"] = all_profiles
    return score_result


@router.get(
    "/reference-standards",
    summary="Statutory & Dietary Reference Standards Knowledge Base",
    description="Returns verified reference standards (FSSAI, ICMR-NIN 2024, ADA 2026, RSSDI, WHO, EFSA) with primary URLs, access dates, and daily-to-serving share conversions."
)
async def get_reference_standards(share_of_daily: float = 0.15):
    from dataclasses import asdict
    engine = PersonalizedScoringEngine(share_of_daily=share_of_daily)
    return {
        "access_date": "2026-10-24",
        "share_of_daily_applied": share_of_daily,
        "per_serving_limits": {
            "sugar": engine.registry.get_per_serving_benchmark("sugar", share_of_daily),
            "sodium": engine.registry.get_per_serving_benchmark("sodium", share_of_daily),
            "saturated_fat": engine.registry.get_per_serving_benchmark("saturated_fat", share_of_daily),
            "diabetes_snack_carbs": engine.registry.get_per_serving_benchmark("diabetes_carbs", share_of_daily),
        },
        "statutory_claim_rules": [asdict(v) for v in FSSAI_CLAIM_RULES.values()],
        "daily_guidelines": [asdict(v) for v in ICMR_NIN_DAILY_LIMITS.values()],
        "diabetes_clinical_guidance": [asdict(v) for v in DIABETES_CLINICAL_GUIDANCE.values()],
        "global_standards": [asdict(v) for v in GLOBAL_REFERENCES.values()],
        "third_party_lab_evidence": THIRD_PARTY_LAB_FRAMEWORK,
    }


@router.get("/health", summary="Health Check")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "tinyfish_api_configured": bool(settings.TINYFISH_API_KEY),
        "database_url": settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else settings.DATABASE_URL,
    }

