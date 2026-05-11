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
            "position": comp.position
        }
        if comp.component_type == "chart" and comp.chart_schema:
            widget["chartSchema"] = comp.chart_schema
            if comp.chart_schema.get("title"):
                widget["title"] = comp.chart_schema["title"]
        elif comp.component_type == "insight" and comp.chart_schema:
            widget["content"] = comp.chart_schema.get("content", "")

        widgets.append(widget)

    # Get version info
    dash_result = await db.execute(select(Dashboard).filter(Dashboard.id == dash_id))
    dash = dash_result.scalars().first()
    version = dash.version if dash else 1

    return {"widgets": widgets, "version": version, "dashboard_id": str(dash_id)}


@router.get("/dashboard/{session_id}")
async def get_dashboard(session_id: str, db: AsyncSession = Depends(get_db)):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    dashboard_id_str = session.metadata.get("dashboard_id")
    if not dashboard_id_str:
        return {"widgets": [], "version": 0, "dashboard_id": None}
        
    dashboard = await get_dashboard_by_id(dashboard_id_str, db)
    dashboard["dashboard_id"] = dashboard_id_str
    return dashboard

@router.get("/dashboard/{session_id}/versions")
async def get_dashboard_versions(session_id: str, db: AsyncSession = Depends(get_db)):
    """List all versions for the current dashboard's lineage."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    dashboard_id_str = session.metadata.get("dashboard_id")
    if not dashboard_id_str:
        return {"versions": []}
        
    import uuid
    dash_id = uuid.UUID(dashboard_id_str)
    result = await db.execute(select(Dashboard).filter(Dashboard.id == dash_id))
    active_dashboard = result.scalars().first()
    if not active_dashboard:
        return {"versions": []}

    result = await db.execute(
        select(Dashboard)
        .filter(Dashboard.name == active_dashboard.name)
        .order_by(Dashboard.version.desc())
    )
    dashboards = result.scalars().all()
    
    return {
        "versions": [
            {"id": str(d.id), "version": d.version, "created_at": d.created_at} 
            for d in dashboards
        ]
    }

@router.post("/dashboard/{session_id}/rollback/{dashboard_id}")
async def rollback_dashboard(session_id: str, dashboard_id: str, db: AsyncSession = Depends(get_db)):
    """Rollback session to a specific dashboard version."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    session.metadata["dashboard_id"] = dashboard_id
    session_manager.save_session(session)
    
    return {"status": "success", "active_dashboard_id": dashboard_id}

@router.post("/dashboard/{session_id}/layout")
async def update_layout(session_id: str, layout: list[dict], db: AsyncSession = Depends(get_db)):
    """Update component positions for the active dashboard."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    dashboard_id_str = session.metadata.get("dashboard_id")
    if not dashboard_id_str:
        raise HTTPException(status_code=404, detail="No active dashboard")
        
    import uuid
    dash_id = uuid.UUID(dashboard_id_str)
    
    for item in layout:
        comp_id = uuid.UUID(item["id"])
        pos = item["position"]
        # Update component position in DB
        from ..db.models import DashboardComponent
        result = await db.execute(select(DashboardComponent).filter(DashboardComponent.id == comp_id))
        comp = result.scalars().first()
        if comp:
            comp.position = pos
            
    await db.commit()
    return {"status": "success"}
