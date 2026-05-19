"""
Pydantic request/response models for the Insights API.

All models use extra="forbid" so stray fields surface immediately
rather than being silently ignored.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Dataset / Upload Models ───────────────────────────────────────────────────

class DatasetMetadata(BaseModel):
    """Full metadata for an uploaded dataset (returned on upload and fetch)."""

    filename: str
    dataset_id: str
    file_path: str = ""            # Kept for backward compat — always empty string
    rows: int
    columns: List[str] = Field(default_factory=list)
    dtypes: Dict[str, str] = Field(default_factory=dict)
    missing_values: Dict[str, int] = Field(default_factory=dict)
    preview_rows: List[Dict[str, Any]] = Field(default_factory=list)
    size_bytes: int = 0
    uploaded_at: Optional[datetime] = None

    model_config = {"extra": "forbid"}


class UploadResponse(BaseModel):
    """Response returned after a successful CSV upload."""

    session_id: str
    dashboard_id: Optional[str] = None
    message: str
    metadata: DatasetMetadata
    default_chart_schemas: List[Dict[str, Any]] = Field(default_factory=list)
    auto_insights: str = ""

    model_config = {"extra": "forbid"}


# ── Chat Models ───────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Inbound chat message from the frontend."""

    session_id: str                          # Equals dataset_id in all current flows
    message: str
    parsed_command: Optional[Dict[str, Any]] = None   # Pre-classified command dict

    model_config = {"extra": "forbid"}


class ChatResponse(BaseModel):
    """Outbound chat response from the backend."""

    content: str
    chart_schema: Optional[Dict[str, Any]] = None
    execution_time_ms: Optional[int] = None
    dashboard_id: Optional[str] = None
    version: Optional[int] = None

    model_config = {"extra": "forbid"}


# ── Session Model ─────────────────────────────────────────────────────────────

class SessionModel(BaseModel):
    """In-memory session state (legacy; DB is the primary store)."""

    session_id: str
    created_at: datetime
    last_accessed_at: datetime
    dataset: Optional[DatasetMetadata] = None
    chat_history: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}
