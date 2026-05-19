"""
Chat route — processes user messages and returns analysis responses.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.db.database import get_db
from src.app.models.session import ChatRequest, ChatResponse
from src.app.utils.langsmith_tracer import trace_async_function
from src.app.utils.logger import get_logger
from src.app.workflows.pipeline import process_chat_request

logger = get_logger(__name__)
router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
@trace_async_function(name="chat_endpoint", tags=["chat", "api"])
async def chat(
    request: ChatRequest, db: AsyncSession = Depends(get_db)
) -> ChatResponse:
    """Process a chat message and return an AI analysis response."""
    logger.info(f"Chat endpoint called — dataset/session: {request.session_id}")
    # In the refactored system, session_id from the frontend is the dataset_id
    return await process_chat_request(
        request.session_id, request.message, db, request.parsed_command
    )
