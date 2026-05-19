"""
LangSmith tracing configuration and decorators.

Provides a singleton tracer manager and decorators for annotating synchronous
and asynchronous functions with LangSmith execution traces.
"""

import functools
import importlib
import inspect
import os
from datetime import datetime
from typing import Any, Callable, Optional

from src.app.config.settings import get_settings
from src.app.utils.logger import get_logger

logger = get_logger(__name__)


class LangSmithTracer:
    """Singleton manager for LangSmith tracing configuration."""

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
        """Set LangChain environment variables and initialise the LangSmith client."""
        if not self.enabled:
            logger.info("LangSmith tracing is disabled")
            return

        try:
            if self.settings.LANGSMITH_API_KEY:
                os.environ["LANGCHAIN_API_KEY"] = self.settings.LANGSMITH_API_KEY

            os.environ["LANGCHAIN_ENDPOINT"] = (
                self.settings.LANGSMITH_ENDPOINT
                or "https://api.smith.langchain.com"
            )

            if self.settings.LANGSMITH_PROJECT:
                os.environ["LANGCHAIN_PROJECT"] = self.settings.LANGSMITH_PROJECT

            os.environ["LANGCHAIN_TRACING_V2"] = "true"

            # Attempt to initialise the LangSmith client if the package is available
            try:
                langsmith_module = importlib.import_module("langsmith")
                client_cls = getattr(langsmith_module, "Client", None)
                if client_cls:
                    self._client = client_cls(
                        api_key=self.settings.LANGSMITH_API_KEY,
                        endpoint=(
                            self.settings.LANGSMITH_ENDPOINT
                            or "https://api.smith.langchain.com"
                        ),
                    )
            except Exception as client_err:
                self._client = None
                logger.warning(
                    f"LangSmith client unavailable — "
                    f"continuing with env-based tracing: {client_err}"
                )

            logger.info(
                f"LangSmith tracing initialised — "
                f"project: {self.settings.LANGSMITH_PROJECT}"
            )

        except Exception as init_err:
            logger.warning(f"Failed to initialise LangSmith: {init_err}")
            self.enabled = False

    @property
    def client(self) -> Optional[Any]:
        if self._client is None and self.enabled:
            self.initialize()
        return self._client

    def is_enabled(self) -> bool:
        return self.enabled


def get_langsmith_tracer() -> LangSmithTracer:
    """Return the singleton LangSmith tracer instance."""
    return LangSmithTracer()


def trace_function(
    name: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> Callable:
    """
    Decorator for tracing both sync and async function execution with LangSmith.

    Falls through immediately if tracing is disabled — zero overhead.
    """
    tracer = get_langsmith_tracer()

    def decorator(func: Callable) -> Callable:
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            if not tracer.is_enabled():
                return await func(*args, **kwargs)
            trace_name = name or func.__name__
            try:
                logger.debug(f"Starting trace: {trace_name}")
                result = await func(*args, **kwargs)
                logger.debug(f"Completed trace: {trace_name}")
                return result
            except Exception as err:
                logger.error(f"Error in traced function {trace_name}: {err}")
                raise

        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            if not tracer.is_enabled():
                return func(*args, **kwargs)
            trace_name = name or func.__name__
            try:
                logger.debug(f"Starting trace: {trace_name}")
                result = func(*args, **kwargs)
                logger.debug(f"Completed trace: {trace_name}")
                return result
            except Exception as err:
                logger.error(f"Error in traced function {trace_name}: {err}")
                raise

        if inspect.iscoroutinefunction(func):
            return functools.wraps(func)(async_wrapper)
        return functools.wraps(func)(sync_wrapper)

    return decorator


def trace_async_function(
    name: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> Callable:
    """Decorator specifically for async function tracing."""
    tracer = get_langsmith_tracer()

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not tracer.is_enabled():
                return await func(*args, **kwargs)
            trace_name = name or func.__name__
            try:
                logger.debug(f"Starting async trace: {trace_name}")
                result = await func(*args, **kwargs)
                logger.debug(f"Completed async trace: {trace_name}")
                return result
            except Exception as err:
                logger.error(f"Error in async traced function {trace_name}: {err}")
                raise

        return wrapper

    return decorator


def create_run_context(
    name: str,
    input_data: dict[str, Any],
    tags: Optional[list[str]] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    """Create a run context dict for manual trace annotation. Returns None if disabled."""
    tracer = get_langsmith_tracer()

    if not tracer.is_enabled() or not tracer.client:
        return None

    try:
        return {
            "name": name,
            "run_type": "chain",
            "inputs": input_data,
            "tags": tags or [],
            "extra": metadata or {},
            "start_time": datetime.utcnow(),
        }
    except Exception as err:
        logger.warning(f"Failed to create run context: {err}")
        return None
