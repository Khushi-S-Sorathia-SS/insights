"""
Dashboard route for fetching persisted dashboard state.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db.database import get_db
from ..db.models import Dashboard, DashboardComponent
from ..storage.session_manager import session_manager

router = APIRouter()

@router.get("/dashboard/by-id/{dashboard_id}")
async def get_dashboard_by_id(dashboard_id: str, db: AsyncSession = Depends(get_db)):
    """Fetch dashboard widgets directly by dashboard UUID. Does NOT require an active session."""
    import uuid
    try:
        dash_id = uuid.UUID(dashboard_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dashboard ID format")

    result = await db.execute(
        select(DashboardComponent)
        .filter(DashboardComponent.dashboard_id == dash_id)
        .order_by(DashboardComponent.id)
    )
    components = result.scalars().all()

    widgets = []
    for comp in components:
        widget = {
            "id": str(comp.id),
            "type": comp.component_type,
            "title": "InsightAI Analysis",
        }
        if comp.component_type == "chart" and comp.chart_schema:
            widget["chartSchema"] = comp.chart_schema
            if comp.chart_schema.get("title"):
                widget["title"] = comp.chart_schema["title"]
        elif comp.component_type == "insight" and comp.chart_schema:
            widget["content"] = comp.chart_schema.get("content", "")

        widgets.append(widget)

    return {"widgets": widgets}


@router.get("/dashboard/{session_id}")
async def get_dashboard(session_id: str, db: AsyncSession = Depends(get_db)):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    dashboard_id_str = session.metadata.get("dashboard_id")
    if not dashboard_id_str:
        return {"widgets": []}
        
    import uuid
    try:
        dash_id = uuid.UUID(dashboard_id_str)
    except ValueError:
        return {"widgets": []}
        
    result = await db.execute(
        select(DashboardComponent)
        .filter(DashboardComponent.dashboard_id == dash_id)
        .order_by(DashboardComponent.id)
    )
    components = result.scalars().all()
    
    widgets = []
    for comp in components:
        widget = {
            "id": str(comp.id),
            "type": comp.component_type,
            "title": "InsightAI Analysis",
        }
        if comp.component_type == "chart" and comp.chart_schema:
            widget["chartSchema"] = comp.chart_schema
            if comp.chart_schema.get("title"):
                widget["title"] = comp.chart_schema["title"]
        elif comp.component_type == "insight" and comp.chart_schema:
            widget["content"] = comp.chart_schema.get("content", "")
            
        widgets.append(widget)
        
    return {"widgets": widgets}
