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
    AlternativesRequest,
    AlternativesResponse,
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
from app.services.recommendation_service import recommendation_service
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
        conditions = request.conditions or ([request.profile] if request.profile else ["general_health"])

        result = await orchestrator.audit_product(
            session=db,
            query=request.query,
            force_refresh=request.force_refresh,
            conditions=conditions,
            user_allergens=request.user_allergens or [],
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
    description="Accepts an uploaded image file of product packaging and extracts the identified product name using OCR & brand detection."
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
    summary="Instant Personalised Rating Calculation",
    description="Calculates Personalised Rating (1-10, lower=better) and Allergy Check."
)
async def score_personal(request: PersonalizeRequest):
    conditions = request.conditions or ([request.profile] if request.profile else ["general_health"])
    score_result = scoring_engine.evaluate(
        product_data=request.product_data,
        selected_conditions=conditions,
        user_allergens=request.user_allergens or [],
    )
    return score_result


@router.post(
    "/products/{product_id}/alternatives",
    response_model=AlternativesResponse,
    summary="Get Better Alternatives for a Product",
    description="Returns 1 to 5 healthier alternatives for the given product if triggered by poor rating or allergen conflict."
)
async def get_product_alternatives(
    product_id: int,
    request: AlternativesRequest,
    db: AsyncSession = Depends(get_db),
):
    conditions = list(request.conditions or [])
    user_allergens = list(request.user_allergens or [])
    if request.allergens:
        for a in request.allergens:
            if a not in user_allergens:
                user_allergens.append(a)

    if isinstance(request.profile, dict):
        if "allergens" in request.profile and isinstance(request.profile["allergens"], list):
            for a in request.profile["allergens"]:
                if a not in user_allergens:
                    user_allergens.append(a)
        if "conditions" in request.profile and isinstance(request.profile["conditions"], list):
            for c in request.profile["conditions"]:
                if c not in conditions:
                    conditions.append(c)
    elif isinstance(request.profile, str) and request.profile and request.profile != "general_health":
        if request.profile not in conditions:
            conditions.append(request.profile)

    if not conditions:
        conditions = ["general_health"]

    return await recommendation_service.get_alternatives(
        searched_product_id=product_id,
        searched_product_data=request.product_data,
        conditions=conditions,
        user_allergens=user_allergens,
        session=db,
    )


@router.post(
    "/recommendations",
    summary="Category Recommendations",
    description="Rank alternative products in the same category by Personalised Rating, excluding unsafe allergens and breaking ties by fewer misleading or contradicted claims."
)
async def get_recommendations(
    request: PersonalizeRequest,
    db: AsyncSession = Depends(get_db),
):
    conditions = request.conditions or ([request.profile] if request.profile else ["general_health"])
    stmt = select(EvidenceLog).order_by(desc(EvidenceLog.created_at)).limit(50)
    db_res = await db.execute(stmt)
    records = db_res.scalars().all()
    candidate_products = [r.product_data for r in records if r.product_data]

    ranked = scoring_engine.rank_recommendations(
        current_product=request.product_data,
        candidate_products=candidate_products,
        selected_conditions=conditions,
        user_allergens=request.user_allergens or [],
    )
    return ranked


@router.get(
    "/reference-standards",
    summary="Statutory & Dietary Reference Standards Knowledge Base",
    description="Returns verified reference standards (FSSAI, ICMR-NIN 2024, ADA 2026, RSSDI, WHO, EFSA) with primary URLs, access dates, and daily-to-serving share conversions."
)
async def get_reference_standards(share_of_daily: float = 0.15):
    from dataclasses import asdict
    registry = ReferenceStandardsRegistry(default_share_of_daily=share_of_daily)
    return {
        "access_date": "2026-10-24",
        "share_of_daily_applied": share_of_daily,
        "per_serving_limits": {
            "sugar": registry.get_per_serving_benchmark("sugar", share_of_daily),
            "sodium": registry.get_per_serving_benchmark("sodium", share_of_daily),
            "saturated_fat": registry.get_per_serving_benchmark("saturated_fat", share_of_daily),
            "diabetes_snack_carbs": registry.get_per_serving_benchmark("diabetes_carbs", share_of_daily),
        },
        "statutory_claim_rules": [asdict(v) for v in FSSAI_CLAIM_RULES.values()],
        "daily_guidelines": [asdict(v) for v in ICMR_NIN_DAILY_LIMITS.values()],
        "diabetes_clinical_guidance": [asdict(v) for v in DIABETES_CLINICAL_GUIDANCE.values()],
        "global_standards": [asdict(v) for v in GLOBAL_REFERENCES.values()],
        "third_party_lab_evidence": THIRD_PARTY_LAB_FRAMEWORK,
    }


@router.get(
    "/independent-evidence",
    summary="Independent Lab & Regulatory Evidence Registry",
    description="Returns independent lab & regulatory reports with tiers, age badges, and acceptance verification for a product query."
)
async def get_independent_evidence(query: str = "", product_name: str = "", brand: str = "", category: str = ""):
    from app.services.independent_evidence_service import IndependentEvidenceService
    svc = IndependentEvidenceService()
    return svc.get_evidence_for_product(query=query, product_name=product_name, brand=brand, category=category)


@router.get("/health", summary="Health Check")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "tinyfish_api_configured": bool(settings.TINYFISH_API_KEY),
        "database_url": settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else settings.DATABASE_URL,
    }
