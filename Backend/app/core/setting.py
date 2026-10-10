"""
Application settings loaded from .env
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # DB
    database_url: str = "sqlite:///./spend_analyser.db"

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # LLM keys (optional – whichever is set gets used)
    anthropic_api_key: str = ""
    google_api_key: str = ""
    groq_api_key: str = ""
    openrouter_api_key: str = ""

    # LLM provider order (comma-separated)
    llm_provider_order: str = "claude,gemini,groq,openrouter"

    # Thresholds
    categorisation_confidence_threshold: float = 0.8
    reconcile_match_threshold: float = 0.7
    reconcile_gap_threshold_pct: float = 0.10
    reconcile_gap_threshold_abs: float = 500.0
    fuzzy_merchant_threshold: int = 90

    # File storage
    upload_dir: str = "./uploads"


settings = Settings()
