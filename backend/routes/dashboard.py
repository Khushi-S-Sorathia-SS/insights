"""
Dashboard route for fetching persisted dashboard state (Dataset-Centric).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import datetime

from ..db.database import get_db
from ..db.models import Dashboard, DashboardComponent

router = APIRouter()

@router.get("/dashboard/by-id/{dashboard_id}")
async def get_dashboard_by_id(dashboard_id: str, db: AsyncSession = Depends(get_db)):
    """Fetch dashboard widgets directly by dashboard UUID."""
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
    active_version = dash.active_version if dash else 1

    return {
        "widgets": widgets, 
        "version": version, 
        "active_version": active_version,
        "dashboard_id": str(dash_id)
    }


@router.get("/dashboard/{dataset_id}")
async def get_dashboard(dataset_id: str, db: AsyncSession = Depends(get_db)):
    """Fetch dashboard state for a specific dataset workspace."""
    try:
        ds_id = uuid.UUID(dataset_id)
    except ValueError:
        # Fallback for legacy session IDs if needed, but here we enforce UUID
        raise HTTPException(status_code=400, detail="Invalid dataset ID format")
        
    result = await db.execute(
        select(Dashboard)
        .filter(Dashboard.dataset_id == ds_id)
        .order_by(Dashboard.version.desc())
    )
    dashboard = result.scalars().first()
    
    if not dashboard:
        return {"widgets": [], "version": 0, "dashboard_id": None}
        
    return await get_dashboard_by_id(str(dashboard.id), db)


@router.get("/dashboard/{dataset_id}/versions")
async def get_dashboard_versions(dataset_id: str, db: AsyncSession = Depends(get_db)):
    """List all versions for the dataset's dashboard lineage."""
    try:
        ds_id = uuid.UUID(dataset_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dataset ID format")
        
    result = await db.execute(
        select(Dashboard)
        .filter(Dashboard.dataset_id == ds_id)
        .order_by(Dashboard.version.desc())
    )
    dashboards = result.scalars().all()
    
    return {
        "versions": [
            {
                "id": str(d.id), 
                "version": d.version, 
                "created_at": d.created_at
            }
            for d in dashboards
        ]
    }


@router.post("/dashboard/{dataset_id}/rollback/{dashboard_id}")
async def rollback_dashboard(dataset_id: str, dashboard_id: str, db: AsyncSession = Depends(get_db)):
    """Rollback workspace to a specific dashboard version."""
    # Since we use UUIDs for dashboards, we can just return success if it exists
    # The frontend will then use get_dashboard_by_id to load it.
    try:
        dash_id = uuid.UUID(dashboard_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dashboard ID format")
        
    result = await db.execute(select(Dashboard).filter(Dashboard.id == dash_id))
    dashboard = result.scalars().first()
    
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard version not found")
        
    return {"status": "success", "active_dashboard_id": str(dash_id)}


@router.post("/dashboard/{dataset_id}/layout")
async def update_layout(dataset_id: str, layout: list[dict], db: AsyncSession = Depends(get_db)):
    """Update component positions for the workspace's dashboard (Auto-save)."""
    try:
        ds_id = uuid.UUID(dataset_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dataset ID format")
        
    result = await db.execute(
        select(Dashboard)
        .filter(Dashboard.dataset_id == ds_id)
        .order_by(Dashboard.version.desc())
    )
    dashboard = result.scalars().first()
    
    if not dashboard:
        raise HTTPException(status_code=404, detail="No dashboard found for this dataset")
    
    for item in layout:
        try:
            comp_id = uuid.UUID(item["id"])
            pos = item["position"]
            
            comp_result = await db.execute(
                select(DashboardComponent)
                .filter(DashboardComponent.id == comp_id)
                .filter(DashboardComponent.dashboard_id == dashboard.id)
            )
            comp = comp_result.scalars().first()
            if comp:
                comp.position = pos
        except (ValueError, KeyError):
            continue
            
    dashboard.last_layout_update = datetime.datetime.utcnow()
    await db.commit()
    
    return {"status": "success", "last_updated": dashboard.last_layout_update}


@router.post("/dashboard/{dataset_id}/save")
async def save_dashboard_version(dataset_id: str, layout: list[dict], db: AsyncSession = Depends(get_db)):
    """Create a new version snapshot of the dashboard with updated layout positions."""
    try:
        ds_id = uuid.UUID(dataset_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dataset ID format")
        
    # Get the current latest version
    result = await db.execute(
        select(Dashboard)
        .filter(Dashboard.dataset_id == ds_id)
        .order_by(Dashboard.version.desc())
    )
    latest_dash = result.scalars().first()
    
    if not latest_dash:
        raise HTTPException(status_code=404, detail="No dashboard found for this dataset")
    
    # Create new dashboard record
    new_version = latest_dash.version + 1
    new_dash = Dashboard(
        dataset_id=ds_id,
        name=latest_dash.name,
        layout_json=latest_dash.layout_json,
        version=new_version,
        active_version=new_version
    )
    db.add(new_dash)
    await db.flush() # Get new_dash.id
    
    # Copy and update components
    for item in layout:
        try:
            comp_id = uuid.UUID(item["id"])
            pos = item["position"]
            
            # Find original component
            comp_result = await db.execute(
                select(DashboardComponent)
                .filter(DashboardComponent.id == comp_id)
            )
            old_comp = comp_result.scalars().first()
            
            if old_comp:
                # Create NEW component for the NEW dashboard
                new_comp = DashboardComponent(
                    dashboard_id=new_dash.id,
                    query_plan=old_comp.query_plan,
                    position=pos,
                    component_type=old_comp.component_type,
                    chart_schema=old_comp.chart_schema
                )
                db.add(new_comp)
        except (ValueError, KeyError):
            continue
            
    await db.commit()
    
    return await get_dashboard_by_id(str(new_dash.id), db)
