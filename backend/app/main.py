import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.api.routes import router as api_router
from app.api.auth_routes import router as auth_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("labeltruth")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.getenv("TESTING"):
        logger.info("Initializing LabelTruth Backend Service...")
        await init_db()
        logger.info("LabelTruth ready to audit packaged foods claims.")
    yield
    if not os.getenv("TESTING"):
        logger.info("Shutting down LabelTruth Backend Service...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Indian Packaged Foods Claims Auditor & Nutrition Comparator (Phase 1)",
    lifespan=lifespan,
)

# CORS Middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API endpoints (both with and without /api prefix for maximum flexibility)
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(api_router)
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(auth_router)


@app.get("/")
def root():
    return {
        "message": "Welcome to LabelTruth API - Indian Packaged Foods Claims Auditor",
        "docs": "/docs",
        "health": "/api/health",
        "audit_endpoint": "/api/audit",
    }

