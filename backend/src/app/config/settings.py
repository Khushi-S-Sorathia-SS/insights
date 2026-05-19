"""
Configuration loader for the Insights application.
Loads environment variables from backend/.env and provides
centralized, validated config access via get_settings().

All fields here are env-driven. Static/non-env constants live in app_config.py.
"""

import json
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "Insights Chatbot"
    APP_VERSION: str = "1.0.0"
    FASTAPI_ENV: str = "development"
    DEBUG: bool = False

    # ── Server ───────────────────────────────────────────────────────────────
    FASTAPI_HOST: str = "127.0.0.1"
    FASTAPI_PORT: int = 8000

    # ── Azure OpenAI ─────────────────────────────────────────────────────────
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_API_VERSION: str = "2024-12-01-preview"
    AZURE_OPENAI_MODEL_NAME: str = "gpt-4.1"
    AZURE_OPENAI_DEPLOYMENT_NAME: str

    # ── LLM Temperatures (per role) ───────────────────────────────────────────
    # Agent planner needs slight creativity for code generation
    LLM_TEMPERATURE_AGENT: float = 0.1
    # Intent classifier must be fully deterministic
    LLM_TEMPERATURE_CLASSIFIER: float = 0.0
    # NLP query executor must be fully deterministic
    LLM_TEMPERATURE_NLP: float = 0.0

    # ── LangSmith Tracing ────────────────────────────────────────────────────
    LANGSMITH_TRACING: str = "false"
    LANGSMITH_ENDPOINT: str = ""
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "Insights"

    # ── Sandbox Configuration ────────────────────────────────────────────────
    DAYTONA_API_KEY: str = ""
    SANDBOX_TIMEOUT: int = 20
    MAX_UPLOAD_SIZE: int = 10485760  # 10 MB in bytes

    # ── PostgreSQL ───────────────────────────────────────────────────────────
    POSTGRES_URI: str

    # ── Session ──────────────────────────────────────────────────────────────
    SESSION_TIMEOUT_HOURS: int = 24
    CLEANUP_INTERVAL_MINUTES: int = 30

    # ── Logging ──────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # ── CORS ─────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8000"

    # ── Frontend URL ─────────────────────────────────────────────────────────
    NEXT_PUBLIC_API_URL: str = "http://localhost:8000"

    # ── Dataset Preview ──────────────────────────────────────────────────────
    PREVIEW_ROWS_COUNT: int = 5

    # ── Dashboard Grid Layout ────────────────────────────────────────────────
    GRID_COLUMNS: int = 12
    DEFAULT_WIDGET_WIDTH: int = 6
    DEFAULT_WIDGET_HEIGHT: int = 4
    INSIGHT_WIDGET_HEIGHT: int = 3

    # ── Computed properties ──────────────────────────────────────────────────

    @property
    def allowed_origins(self) -> list[str]:
        """Parse ALLOWED_ORIGINS into a list, supporting both comma-separated and JSON list strings."""
        origins = self.ALLOWED_ORIGINS.strip()
        if not origins:
            return []
        if origins.startswith("["):
            try:
                parsed = json.loads(origins)
                if isinstance(parsed, list):
                    return [str(o).strip() for o in parsed if str(o).strip()]
            except json.JSONDecodeError:
                pass
        return [o.strip() for o in origins.split(",") if o.strip()]

    # ── Validators ───────────────────────────────────────────────────────────

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value: object) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "y"}:
                return True
            if normalized in {"false", "0", "no", "n"}:
                return False
        return False

    # ── Helper methods ───────────────────────────────────────────────────────

    def validate_required(self) -> None:
        """Validate that all critical credentials are present at startup."""
        if not self.AZURE_OPENAI_API_KEY:
            raise ValueError("AZURE_OPENAI_API_KEY is not set in backend/.env")
        if not self.AZURE_OPENAI_ENDPOINT:
            raise ValueError("AZURE_OPENAI_ENDPOINT is not set in backend/.env")
        if not self.AZURE_OPENAI_DEPLOYMENT_NAME:
            raise ValueError("AZURE_OPENAI_DEPLOYMENT_NAME is not set in backend/.env")
        if not self.POSTGRES_URI:
            raise ValueError("POSTGRES_URI is not set in backend/.env")

    def is_production(self) -> bool:
        return self.FASTAPI_ENV == "production"

    def is_development(self) -> bool:
        return self.FASTAPI_ENV == "development"

    model_config = {
        # Loaded from backend/.env when running uvicorn from inside backend/
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        # Forbid unknown env keys — prevents silent typos in config
        "extra": "forbid",
    }


@lru_cache()
def get_settings() -> Settings:
    """Return a cached, validated Settings instance.

    The cache ensures the .env file is read exactly once per process.
    Use get_settings() everywhere — never instantiate Settings() directly.
    """
    settings = Settings()
    settings.validate_required()
    return settings
