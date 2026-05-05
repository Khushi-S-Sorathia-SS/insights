"""
Upload route for CSV dataset ingestion.
"""

from fastapi import APIRouter, File, UploadFile

from ..models.session import UploadResponse
from ..storage.file_manager import file_manager
from ..storage.session_manager import session_manager
from ..utils.error_handler import SandboxError
from ..workflows.agent_planner import generate_analysis_code

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_csv(file: UploadFile = File(...)) -> UploadResponse:
    session = session_manager.create_session()
    metadata = file_manager.save_uploaded_csv(file, session.session_id)
    session.dataset = metadata
    session_manager.save_session(session)

    default_chart_urls: list[str] = []
    auto_insights: str = ""

    try:
        result = generate_analysis_code(
            "Create 3-4 visualizations to provide an initial overview of this dataset. Generate charts like distribution plots, count plots, or correlation heatmaps. Then provide a brief summary of key insights.",
            metadata,
        )
        auto_insights = result.get("output", "Could not generate initial dataset insights.")
        default_chart_urls = result.get("charts", [])
    except SandboxError:
        default_chart_urls = []
        auto_insights = "Could not generate initial dataset insights."

    return UploadResponse(
        session_id=session.session_id,
        message="Upload successful",
        metadata=metadata,
        default_chart_urls=default_chart_urls,
        auto_insights=auto_insights,
    )
