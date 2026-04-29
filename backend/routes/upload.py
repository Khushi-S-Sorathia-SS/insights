"""
Upload route for CSV dataset ingestion.
"""

from fastapi import APIRouter, File, UploadFile

from ..models.session import UploadResponse
from ..storage.file_manager import file_manager
from ..storage.session_manager import session_manager

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_csv(file: UploadFile = File(...)) -> UploadResponse:
    session = session_manager.create_session()
    metadata = file_manager.save_uploaded_csv(file, session.session_id)
    session.dataset = metadata
    session_manager.save_session(session)

    return UploadResponse(
        session_id=session.session_id,
        message="Upload successful",
        metadata=metadata,
    )
