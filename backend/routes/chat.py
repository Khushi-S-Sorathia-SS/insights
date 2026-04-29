"""
Chat route for dataset analysis queries.
"""

from fastapi import APIRouter

from ..models.session import ChatRequest, ChatResponse
from ..workflows.pipeline import process_chat_request

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    return process_chat_request(request.session_id, request.message)
