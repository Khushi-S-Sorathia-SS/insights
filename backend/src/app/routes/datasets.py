"""
Datasets route — list datasets, fetch metadata, fetch chat history.

display_name is mandatory (NOT NULL in DB, required at upload) — no fallback
to filename anywhere in this module.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.db.database import get_db
from src.app.db.models import ChatMessage, Dataset
from src.app.models.session import DatasetMetadata

router = APIRouter()


@router.get("/datasets")
async def list_datasets(db: AsyncSession = Depends(get_db)) -> list[dict]:
    """List all uploaded datasets ordered by most recent first."""
    result = await db.execute(
        select(Dataset).order_by(Dataset.uploaded_at.desc())
    )
    datasets = result.scalars().all()

    return [
        {
            "id": str(d.id),
            "filename": d.filename,
            "display_name": d.display_name,  # Mandatory — no fallback
            "uploaded_at": d.uploaded_at,
            "rows": d.schema_json.get("rows", 0) if d.schema_json else 0,
        }
        for d in datasets
    ]


@router.get("/datasets/{dataset_id}", response_model=DatasetMetadata)
async def get_dataset_metadata(
    dataset_id: str, db: AsyncSession = Depends(get_db)
) -> DatasetMetadata:
    """Fetch full metadata for a specific dataset."""
    try:
        ds_id = uuid.UUID(dataset_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dataset ID format")

    result = await db.execute(select(Dataset).filter(Dataset.id == ds_id))
    dataset = result.scalars().first()

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    return DatasetMetadata(
        filename=dataset.filename,
        dataset_id=str(dataset.id),
        file_path="",  # No disk storage — data lives in PostgreSQL
        rows=dataset.schema_json.get("rows", 0),
        columns=dataset.schema_json.get("columns", []),
        dtypes=dataset.schema_json.get("dtypes", {}),
        missing_values=dataset.schema_json.get("missing_values", {}),
        preview_rows=dataset.schema_json.get("preview_rows", []),
        size_bytes=dataset.schema_json.get("size_bytes", 0),
        uploaded_at=dataset.uploaded_at,
    )


@router.get("/datasets/{dataset_id}/history")
async def get_chat_history(
    dataset_id: str, db: AsyncSession = Depends(get_db)
) -> list[dict]:
    """Fetch the persistent chat history for a dataset workspace."""
    try:
        ds_id = uuid.UUID(dataset_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dataset ID format")

    result = await db.execute(
        select(ChatMessage)
        .filter(ChatMessage.dataset_id == ds_id)
        .order_by(ChatMessage.created_at.asc())
    )
    messages = result.scalars().all()

    return [
        {
            "role": m.role,
            "content": m.content,
            "chart_schema": m.chart_schema,
            "execution_time_ms": m.execution_time_ms,
            "timestamp": m.created_at,
        }
        for m in messages
    ]
