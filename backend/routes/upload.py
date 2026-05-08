"""
Upload route for CSV dataset ingestion.
"""

import asyncio
from fastapi import APIRouter, File, UploadFile, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.database import get_db
from ..semantic.semantic_layer import get_chart_rules

from ..models.session import UploadResponse
from ..storage.file_manager import file_manager
from ..storage.session_manager import session_manager
from ..utils.error_handler import SandboxError
from ..workflows.agent_planner import generate_analysis_code

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
) -> UploadResponse:
    session = session_manager.create_session()
    metadata = await file_manager.save_uploaded_csv(file, session.session_id, db)
    session.dataset = metadata
    session_manager.save_session(session)

    default_chart_schemas: list[dict] = []
    auto_insights: str = ""

    file.file.seek(0)
    raw_data = file.file.read()
    
    chart_rules = await get_chart_rules(db)

    try:
        result = await asyncio.to_thread(
            generate_analysis_code,
            "Create 3-4 visualizations to provide an initial overview of this dataset. Generate diverse charts according to the provided schema rules. Then provide a brief summary of key insights.",
            metadata,
            raw_data,
            chart_rules
        )
        auto_insights = result.get("output", "Could not generate initial dataset insights.")
        default_chart_schemas = result.get("chart_schemas", [])
    except SandboxError:
        default_chart_schemas = []
        auto_insights = "Could not generate initial dataset insights."

    # Persist the dashboard and its components to the database
    from ..db.models import Dashboard, DashboardComponent
    
    dashboard = Dashboard(name=f"Dashboard: {metadata.filename}", layout_json={})
    db.add(dashboard)
    await db.commit()
    await db.refresh(dashboard)
    
    # We can save the dashboard ID in the session metadata to link it
    session.metadata["dashboard_id"] = str(dashboard.id)
    session_manager.save_session(session)

    for i, schema in enumerate(default_chart_schemas):
        component = DashboardComponent(
            dashboard_id=dashboard.id,
            position={"x": i % 2, "y": i // 2, "w": 1, "h": 1},
            component_type="chart",
            chart_schema=schema
        )
        db.add(component)
        
    if auto_insights:
        insight_component = DashboardComponent(
            dashboard_id=dashboard.id,
            position={"x": 0, "y": len(default_chart_schemas) // 2 + 1, "w": 2, "h": 1},
            component_type="insight",
            chart_schema={"content": auto_insights}
        )
        db.add(insight_component)
        
    await db.commit()

    return UploadResponse(
        session_id=session.session_id,
        dashboard_id=str(dashboard.id),
        message="Upload successful",
        metadata=metadata,
        default_chart_schemas=default_chart_schemas,
        auto_insights=auto_insights,
    )
