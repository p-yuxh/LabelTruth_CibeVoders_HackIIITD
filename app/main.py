import logging
from contextlib import asynccontextmanager
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.schemas import MergedSignals
from app.pipeline.triage import validate_and_preprocess_image
from app.pipeline.orchestrator import PipelineOrchestrator

# Setup structured logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("labeltruth.main")

orchestrator = PipelineOrchestrator()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting LabelTruth Product Label Analysis Service (Phase 1)...")
    logger.info(f"Using OCR Provider: {settings.ocr_provider}")
    logger.info(f"Using Vision Provider: {settings.vision_provider} (Model: {settings.gemini_model})")
    yield
    logger.info("Shutting down LabelTruth Service...")


app = FastAPI(
    title="LabelTruth Food Product Label Extractor",
    description="Extracts food product signals, ingredients, and nutrition from pack photos.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", summary="Health Check")
async def health_check():
    return {
        "status": "healthy",
        "service": "LabelTruth Product Label Extractor",
        "phase": 1,
    }


@app.post(
    "/analyze",
    response_model=MergedSignals,
    summary="Analyze Food Product Photos",
    description="Accepts 1 to 3 pack photos (PNG/JPG, max 8MB each), extracts barcode, OCR, and vision signals concurrently, and returns merged product signals.",
)
async def analyze_photos(
    files: List[UploadFile] = File(
        ...,
        description="1 to 3 food product pack photos (PNG or JPG format, max 8 MB each)",
    )
):
    # Rule 1: Must accept between 1 and 3 images
    if not files or len(files) < 1 or len(files) > 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Exactly 1 to 3 images must be uploaded. Received {len(files) if files else 0}.",
        )

    preprocessed_images = []
    for file in files:
        raw_bytes = await file.read()
        if not raw_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Uploaded file '{file.filename}' is empty.",
            )

        processed = validate_and_preprocess_image(
            raw_bytes=raw_bytes,
            filename=file.filename,
            content_type=file.content_type,
        )
        preprocessed_images.append(processed)

    # Rule 2: Execute concurrent triage and merge extracted signals
    merged_signals = await orchestrator.analyze_images(preprocessed_images)
    return merged_signals

