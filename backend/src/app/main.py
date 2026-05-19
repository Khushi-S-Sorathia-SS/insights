"""
Insights Backend — FastAPI application entrypoint.

Run from inside the backend/ directory with the venv active:
    python -m uvicorn src.app.main:app --reload

All routes, middleware, and startup/shutdown hooks are registered here.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.app.config.settings import get_settings
from src.app.db.database import init_db
from src.app.routes.chat import router as chat_router
from src.app.routes.dashboard import router as dashboard_router
from src.app.routes.datasets import router as datasets_router
from src.app.routes.upload import router as upload_router
from src.app.utils.error_handler import (
    FileUploadError,
    InsightsException,
    SandboxError,
    SessionError,
)
from src.app.utils.langsmith_tracer import get_langsmith_tracer
from src.app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle hook for the FastAPI application."""
    # ── Startup ────────────────────────────────────────────────────────────────
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.FASTAPI_ENV}")

    await init_db()
    logger.info("Database initialised")

    tracer = get_langsmith_tracer()
    tracer.initialize()

    yield

    # ── Shutdown ───────────────────────────────────────────────────────────────
    logger.info(f"Shutting down {settings.APP_NAME}")


# ── Application factory ───────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered data analytics and visualization backend.",
    docs_url="/docs" if settings.is_development() else None,
    redoc_url="/redoc" if settings.is_development() else None,
    openapi_url="/openapi.json" if settings.is_development() else None,
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception handlers ────────────────────────────────────────────────────────

@app.exception_handler(FileUploadError)
async def file_upload_error_handler(
    request: Request, exc: FileUploadError
) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": exc.code, "message": exc.message})


@app.exception_handler(SessionError)
async def session_error_handler(
    request: Request, exc: SessionError
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"error": exc.code, "message": exc.message})


@app.exception_handler(SandboxError)
async def sandbox_error_handler(
    request: Request, exc: SandboxError
) -> JSONResponse:
    return JSONResponse(status_code=500, content={"error": exc.code, "message": exc.message})


@app.exception_handler(InsightsException)
async def insights_error_handler(
    request: Request, exc: InsightsException
) -> JSONResponse:
    return JSONResponse(status_code=500, content={"error": exc.code, "message": exc.message})


# ── Routes ────────────────────────────────────────────────────────────────────

app.include_router(upload_router,    prefix="/api", tags=["upload"])
app.include_router(chat_router,      prefix="/api", tags=["chat"])
app.include_router(datasets_router,  prefix="/api", tags=["datasets"])
app.include_router(dashboard_router, prefix="/api", tags=["dashboard"])


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["health"])
async def health_check() -> dict:
    """Lightweight liveness probe — returns 200 if the server is running."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.FASTAPI_ENV,
    }
