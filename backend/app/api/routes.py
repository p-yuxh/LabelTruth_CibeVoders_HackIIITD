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
)
from app.services.orchestrator import AuditOrchestrator
from app.services.image_detector import ProductImageDetector
from app.config import settings

logger = logging.getLogger("labeltruth.api")
router = APIRouter()
orchestrator = AuditOrchestrator()
image_detector = ProductImageDetector()


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
    try:
        result = await orchestrator.audit_product(
            session=db,
            query=request.query,
            force_refresh=request.force_refresh,
        )
        return result
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
        
        detection_result = image_detector.detect_product_from_bytes(content)
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
        
        detection_result = image_detector.detect_product_from_bytes(content)
        product_query = detection_result.get("detected_product", "").strip()
        
        if not product_query or product_query == "Packaged Food Product":
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


@router.get("/health", summary="Health Check")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "tinyfish_api_configured": bool(settings.TINYFISH_API_KEY),
        "database_url": settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else settings.DATABASE_URL,
    }

