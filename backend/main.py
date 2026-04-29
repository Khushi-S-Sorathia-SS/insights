"""
FastAPI application entry point for the Insights Chatbot.
Handles routing, middleware, and app initialization.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .utils.error_handler import InsightsException
from .utils.logger import get_logger

# Import routes (to be created in Phase 7)
# from routes import upload, chat

logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    # Startup
    logger.info("Starting Insights Chatbot...")
    logger.info(f"Environment: {settings.FASTAPI_ENV}")
    logger.info(f"Debug: {settings.DEBUG}")
    logger.info(f"Upload directory: {settings.UPLOAD_DIR}")

    yield

    # Shutdown
    logger.info("Shutting down Insights Chatbot...")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered chatbot for employee dataset analysis",
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(InsightsException)
async def insights_exception_handler(request, exc: InsightsException):
    """Handle custom application exceptions."""
    logger.warning(f"Application error: {exc.message}")
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.code,
            "message": exc.message,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "message": "An unexpected error occurred. Please try again later.",
        },
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


# API info endpoint
@app.get("/", tags=["Info"])
async def root():
    """API information endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "AI-powered chatbot for employee dataset analysis",
        "docs": "/docs",
        "redoc": "/redoc",
    }


# Include routers (to be added in Phase 7)
# app.include_router(upload.router, prefix="/api", tags=["Upload"])
# app.include_router(chat.router, prefix="/api", tags=["Chat"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.FASTAPI_HOST,
        port=settings.FASTAPI_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
