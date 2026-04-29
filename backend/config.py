"""
Configuration loader for the Insights Chatbot application.
Loads environment variables and provides centralized config access.
"""

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Insights Chatbot"
    APP_VERSION: str = "1.0.0"
    FASTAPI_ENV: str = os.getenv("FASTAPI_ENV", "development")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # Server
    FASTAPI_HOST: str = os.getenv("FASTAPI_HOST", "127.0.0.1")
    FASTAPI_PORT: int = int(os.getenv("FASTAPI_PORT", "8000"))

    # API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Frontend
    NEXT_PUBLIC_API_URL: str = os.getenv("NEXT_PUBLIC_API_URL", "http://localhost:8000")

    # Sandbox Configuration
    SANDBOX_TIMEOUT: int = int(os.getenv("SANDBOX_TIMEOUT", "20"))
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", "10485760"))  # 10 MB
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "/tmp/uploads")

    # Redis (Optional)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_ENABLED: bool = os.getenv("REDIS_ENABLED", "false").lower() == "true"

    # MongoDB (Optional)
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "insights_chatbot")
    MONGODB_ENABLED: bool = os.getenv("MONGODB_ENABLED", "false").lower() == "true"

    # Session Configuration
    SESSION_TIMEOUT_HOURS: int = int(os.getenv("SESSION_TIMEOUT_HOURS", "24"))
    CLEANUP_INTERVAL_MINUTES: int = int(os.getenv("CLEANUP_INTERVAL_MINUTES", "30"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8000"

    @property
    def allowed_origins(self) -> list[str]:
        origins = self.ALLOWED_ORIGINS.strip()
        if not origins:
            return []
        if origins.startswith("[") or origins.startswith("("):
            try:
                parsed = json.loads(origins)
                if isinstance(parsed, list):
                    return [str(origin).strip() for origin in parsed if str(origin).strip()]
            except json.JSONDecodeError:
                pass
        return [origin.strip() for origin in origins.split(",") if origin.strip()]

    class Config:
        env_file = ".env.local"
        case_sensitive = True

    def validate(self) -> None:
        """Validate critical configuration settings."""
        if not self.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable is not set")

        # Create upload directory if it doesn't exist
        Path(self.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

    def is_production(self) -> bool:
        """Check if running in production."""
        return self.FASTAPI_ENV == "production"

    def is_development(self) -> bool:
        """Check if running in development."""
        return self.FASTAPI_ENV == "development"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    settings.validate()
    return settings


# Constants
ALLOWED_CSV_COLUMNS = {
    "name", "id", "employee_id", "department", "salary",
    "experience", "gender", "age", "position", "hire_date",
    "status", "rating", "attendance", "projects"
}

ALLOWED_IMPORTS = {
    "pandas",
    "numpy",
    "matplotlib",
    "io",
    "base64",
    "json",
}

FORBIDDEN_IMPORTS = {
    "os",
    "sys",
    "subprocess",
    "requests",
    "urllib",
    "pickle",
    "dill",
    "importlib",
    "__import__",
    "eval",
    "exec",
}

# File upload constraints
MAX_UPLOAD_SIZE_MB = 10
ALLOWED_FILE_TYPES = {".csv"}

# Sandbox constraints
DEFAULT_SANDBOX_TIMEOUT = 20  # seconds
DEFAULT_SANDBOX_MEMORY_LIMIT = "512M"

# Response codes
SUCCESS_RESPONSE_CODE = 200
CREATED_RESPONSE_CODE = 201
BAD_REQUEST_CODE = 400
UNAUTHORIZED_CODE = 401
FORBIDDEN_CODE = 403
NOT_FOUND_CODE = 404
INTERNAL_ERROR_CODE = 500
