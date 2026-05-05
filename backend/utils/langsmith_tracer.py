"""
LangSmith tracing configuration and utilities.
Provides tracing setup and decorators for monitoring LLM calls and application workflows.
"""

import importlib
import inspect
import os
import functools
from typing import Any, Callable, Optional
from datetime import datetime

from ..config import get_settings
from .logger import get_logger

logger = get_logger(__name__)


class LangSmithTracer:
    """Manager for LangSmith tracing configuration."""

    _instance: Optional["LangSmithTracer"] = None
    _client: Optional[Any] = None

    def __new__(cls) -> "LangSmithTracer":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        self.settings = get_settings()
        self.enabled = self.settings.LANGSMITH_TRACING.lower() == "true"

    def initialize(self) -> None:
        """Initialize LangSmith client and environment variables."""
        if not self.enabled:
            logger.info("LangSmith tracing is disabled")
            return

        try:
            # Set environment variables for LangChain integration
            if self.settings.LANGSMITH_API_KEY:
                os.environ["LANGCHAIN_API_KEY"] = self.settings.LANGSMITH_API_KEY
            
            if self.settings.LANGSMITH_ENDPOINT:
                os.environ["LANGCHAIN_ENDPOINT"] = self.settings.LANGSMITH_ENDPOINT
            else:
                os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
            
            if self.settings.LANGSMITH_PROJECT:
                os.environ["LANGCHAIN_PROJECT"] = self.settings.LANGSMITH_PROJECT
            
            # Enable tracing
            os.environ["LANGCHAIN_TRACING_V2"] = "true"

            # Try to initialize LangSmith client if the package is available.
            try:
                langsmith_module = importlib.import_module("langsmith")
                client_cls = getattr(langsmith_module, "Client", None)
                if client_cls:
                    self._client = client_cls(
                        api_key=self.settings.LANGSMITH_API_KEY,
                        endpoint=self.settings.LANGSMITH_ENDPOINT or "https://api.smith.langchain.com",
                    )
            except Exception as exc:
                self._client = None
                logger.warning(f"LangSmith client unavailable, continuing with env-based tracing: {exc}")

            logger.info(
                f"LangSmith tracing initialized. "
                f"Project: {self.settings.LANGSMITH_PROJECT}"
            )
        except Exception as e:
            logger.warning(f"Failed to initialize LangSmith: {e}")
            self.enabled = False

    @property
    def client(self) -> Optional[Any]:
        """Get LangSmith client instance."""
        if self._client is None and self.enabled:
            self.initialize()
        return self._client

    def is_enabled(self) -> bool:
        """Check if LangSmith tracing is enabled."""
        return self.enabled


def get_langsmith_tracer() -> LangSmithTracer:
    """Get singleton LangSmith tracer instance."""
    return LangSmithTracer()


def trace_function(name: Optional[str] = None, tags: Optional[list[str]] = None):
    """
    Decorator for tracing function execution with LangSmith.
    
    Args:
        name: Custom name for the traced function. If None, uses function name.
        tags: List of tags to associate with the trace.
    """
    tracer = get_langsmith_tracer()
    
    def decorator(func: Callable) -> Callable:
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            if not tracer.is_enabled():
                return await func(*args, **kwargs)

            trace_name = name or func.__name__
            trace_tags = tags or []

            try:
                logger.debug(f"Starting trace: {trace_name}")
                result = await func(*args, **kwargs)
                logger.debug(f"Completed trace: {trace_name}")
                return result
            except Exception as e:
                logger.error(f"Error in traced function {trace_name}: {str(e)}")
                raise

        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            if not tracer.is_enabled():
                return func(*args, **kwargs)

            trace_name = name or func.__name__
            trace_tags = tags or []

            try:
                logger.debug(f"Starting trace: {trace_name}")
                result = func(*args, **kwargs)
                logger.debug(f"Completed trace: {trace_name}")
                return result
            except Exception as e:
                logger.error(f"Error in traced function {trace_name}: {str(e)}")
                raise

        if inspect.iscoroutinefunction(func):
            return functools.wraps(func)(async_wrapper)
        return functools.wraps(func)(sync_wrapper)

    return decorator


def trace_async_function(name: Optional[str] = None, tags: Optional[list[str]] = None):
    """
    Decorator for tracing async function execution with LangSmith.
    
    Args:
        name: Custom name for the traced function. If None, uses function name.
        tags: List of tags to associate with the trace.
    """
    tracer = get_langsmith_tracer()
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not tracer.is_enabled():
                return await func(*args, **kwargs)
            
            trace_name = name or func.__name__
            trace_tags = tags or []
            
            try:
                logger.debug(f"Starting async trace: {trace_name}")
                result = await func(*args, **kwargs)
                logger.debug(f"Completed async trace: {trace_name}")
                return result
                
            except Exception as e:
                logger.error(f"Error in async traced function {trace_name}: {str(e)}")
                raise
        
        return wrapper
    return decorator


def create_run_context(
    name: str,
    input_data: dict[str, Any],
    tags: Optional[list[str]] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    """
    Create a run context for manual tracing.
    
    Args:
        name: Name of the run
        input_data: Input data for the run
        tags: Optional tags
        metadata: Optional metadata
        
    Returns:
        Run context or None if tracing is disabled
    """
    tracer = get_langsmith_tracer()
    
    if not tracer.is_enabled() or not tracer.client:
        return None
    
    try:
        run_context = {
            "name": name,
            "run_type": "chain",
            "inputs": input_data,
            "tags": tags or [],
            "extra": metadata or {},
            "start_time": datetime.utcnow(),
        }
        return run_context
    except Exception as e:
        logger.warning(f"Failed to create run context: {e}")
        return None
