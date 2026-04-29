"""
Pydantic models for session management and chat messages.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DatasetMetadata(BaseModel):
    """Metadata about the uploaded dataset."""

    filename: str
    file_path: str
    rows: int
    columns: list[str]
    dtypes: dict[str, str]
    missing_values: dict[str, int]
    size_bytes: int
    uploaded_at: datetime

    class Config:
        extra = "forbid"


class ChatMessage(BaseModel):
    """A single message in the chat history."""

    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: datetime
    analysis_result: Optional[dict] = Field(
        default=None, description="Analysis result for Type B queries"
    )
    execution_time_ms: Optional[int] = Field(
        default=None, description="Time taken for code execution"
    )

    class Config:
        extra = "forbid"


class SessionModel(BaseModel):
    """Session data model for storing user session state."""

    session_id: str = Field(..., description="Unique session identifier")
    created_at: datetime
    last_accessed_at: datetime
    dataset: Optional[DatasetMetadata] = Field(default=None, description="Uploaded dataset metadata")
    chat_history: list[ChatMessage] = Field(default_factory=list, description="Chat history")
    metadata: dict = Field(default_factory=dict, description="Additional session metadata")

    class Config:
        extra = "forbid"

    def add_message(self, role: str, content: str, **kwargs) -> None:
        """Add a message to chat history."""
        message = ChatMessage(
            role=role,
            content=content,
            timestamp=datetime.utcnow(),
            **kwargs
        )
        self.chat_history.append(message)
        self.last_accessed_at = datetime.utcnow()

    def get_context(self) -> str:
        """Get chat history as context string."""
        context = ""
        for msg in self.chat_history:
            context += f"{msg.role.upper()}: {msg.content}\n"
        return context


class UploadResponse(BaseModel):
    """Response model for file upload endpoint."""

    session_id: str
    message: str
    metadata: DatasetMetadata

    class Config:
        extra = "forbid"


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    session_id: str
    message: str

    class Config:
        extra = "forbid"


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    role: str = "assistant"
    content: str
    chart_url: Optional[str] = None
    execution_time_ms: Optional[int] = None
    error_message: Optional[str] = None

    class Config:
        extra = "forbid"
