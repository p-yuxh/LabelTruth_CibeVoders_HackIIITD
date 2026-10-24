import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    PROJECT_NAME: str = "LabelTruth API"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/labeltruth"
    # Fallback to local SQLite when PostgreSQL is unavailable
    FALLBACK_DATABASE_URL: str = "sqlite+aiosqlite:///./evidence_log.db"
    
    # TinyFish Web Scraping API (Only external service required)
    TINYFISH_API_KEY: str = os.getenv("TINYFISH_API_KEY", "")

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "*",
    ]

    model_config = SettingsConfigDict(
        env_file=["backend/.env", ".env"],
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
