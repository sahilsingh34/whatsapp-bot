"""
Application configuration loaded from environment variables.
Uses pydantic-settings for type-safe configuration management.
"""

import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

logger = logging.getLogger(__name__)



class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ---- Groq API ----
    GROQ_API_KEY: str = ""

    # ---- WhatsApp Cloud API ----
    WHATSAPP_TOKEN: str
    PHONE_NUMBER_ID: str
    VERIFY_TOKEN: str

    # ---- Database ----
    DATABASE_URL: str = "postgresql+asyncpg://mpc_user:mpc_password@db:5432/mpc_whatsapp"

    # ---- Redis ----
    REDIS_URL: str = "redis://redis:6379/0"

    # ---- Redis Agent Memory ----
    REDIS_MEMORY_ENDPOINT: str = ""
    REDIS_MEMORY_STORE_ID: str = ""
    REDIS_MEMORY_API_KEY: str = ""

    # ---- Redis LangCache ----
    REDIS_LANGCACHE_ENDPOINT: str = ""
    REDIS_LANGCACHE_CACHE_ID: str = ""
    REDIS_LANGCACHE_API_KEY: str = ""

    # ---- Clinic Staff (for escalation) ----
    CLINIC_STAFF_PHONE: str = ""

    # ---- Admin API Key ----
    ADMIN_API_KEY: str = "change-me-in-production"

    # ---- Application ----
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # ---- Clinic Configuration ----
    CLINIC_NAME: str = "My Pain Clinic Global"
    CLINIC_LOCATION: str = "Bandra, Mumbai"
    WORKING_HOUR_START: int = 8    # 8 AM (actual start 8:30)
    WORKING_HOUR_START_MINUTE: int = 30  # 8:30 AM
    WORKING_HOUR_END: int = 20    # 8 PM
    TIMEZONE: str = "Asia/Kolkata"

    # ---- AI Configuration (Groq) ----
    AI_MODEL_SIMPLE: str = "llama-3.1-8b-instant"
    AI_MODEL_COMPLEX: str = "llama-3.3-70b-versatile"
    AI_BASE_URL: str = "https://api.groq.com/openai/v1"
    AI_TEMPERATURE: float = 0.7
    AI_MAX_TOKENS: int = 50
    ENABLE_WEB_SEARCH: bool = True

    # ---- Memory Configuration ----
    CONVERSATION_HISTORY_LIMIT: int = 20
    REDIS_CACHE_TTL: int = 3600       # 1 hour in seconds
    MEMORY_RETENTION_DAYS: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """Returns cached settings instance."""
    settings = Settings()
    logger.info(f"Loaded REDIS_MEMORY_ENDPOINT: '{settings.REDIS_MEMORY_ENDPOINT}'")
    logger.info(f"Loaded REDIS_LANGCACHE_ENDPOINT: '{settings.REDIS_LANGCACHE_ENDPOINT}'")
    return settings

