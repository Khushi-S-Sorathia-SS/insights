"""
Chat route for dataset analysis queries.
Integrated with LangSmith for execution tracing.
"""

from fastapi import APIRouter

from ..models.session import ChatRequest, ChatResponse
from ..workflows.pipeline import process_chat_request
from ..utils.logger import get_logger
from ..utils.langsmith_tracer import trace_async_function

logger = get_logger(__name__)
router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
@trace_async_function(name="chat_endpoint", tags=["chat", "api"])
async def chat(request: ChatRequest) -> ChatResponse:
    """Process a chat message and return analysis."""
    logger.info(f"Chat endpoint called. Session: {request.session_id}")
    return process_chat_request(request.session_id, request.message)
