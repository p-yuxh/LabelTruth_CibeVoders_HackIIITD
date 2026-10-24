import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Google Gemini Vision Configuration
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.5-flash"

    # Tavily API Configuration
    tavily_api_key: Optional[str] = None

    # Pipeline Match Thresholds
    confident_threshold: float = 0.85
    ambiguous_threshold: float = 0.60

    # Cache Database
    database_url: str = "sqlite+aiosqlite:///./cache.db"

    # Providers
    ocr_provider: str = "paddleocr"
    vision_provider: str = "gemini"

    # Image Processing Limits
    max_image_size_bytes: int = 8 * 1024 * 1024  # 8 MB
    max_image_side_px: int = 2000
    allowed_image_types: List[str] = ["image/jpeg", "image/png", "image/jpg"]

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()

