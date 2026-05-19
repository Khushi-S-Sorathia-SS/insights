"""
Dashboard route — fetch dashboard state, manage versions, handle layout updates.
"""

import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.db.database import get_db
from src.app.db.models import Dashboard, DashboardComponent

router = APIRouter()


@router.get("/dashboard/by-id/{dashboard_id}")
async def get_dashboard_by_id(
    dashboard_id: str, db: AsyncSession = Depends(get_db)
) -> dict:
    """Fetch all widgets for a dashboard directly by its UUID."""
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
        widget: dict = {
            "id": str(comp.id),
            "type": comp.component_type,
            "title": "InsightAI Analysis",
            "position": comp.position,
        }
        if comp.component_type == "chart" and comp.chart_schema:
            widget["chartSchema"] = comp.chart_schema
            if comp.chart_schema.get("title"):
                widget["title"] = comp.chart_schema["title"]
        elif comp.component_type == "insight" and comp.chart_schema:
            widget["content"] = comp.chart_schema.get("content", "")
        widgets.append(widget)

    dash_result = await db.execute(
        select(Dashboard).filter(Dashboard.id == dash_id)
    )
    dash = dash_result.scalars().first()
    version = dash.version if dash else 1
    active_version = dash.active_version if dash else 1

    return {
        "widgets": widgets,
        "version": version,
        "active_version": active_version,
        "dashboard_id": str(dash_id),
    }


@router.get("/dashboard/{dataset_id}")
async def get_dashboard(
    dataset_id: str, db: AsyncSession = Depends(get_db)
) -> dict:
    """Fetch the latest dashboard version for a dataset workspace."""
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
        return {"widgets": [], "version": 0, "dashboard_id": None}

    return await get_dashboard_by_id(str(dashboard.id), db)


@router.get("/dashboard/{dataset_id}/versions")
async def get_dashboard_versions(
    dataset_id: str, db: AsyncSession = Depends(get_db)
) -> dict:
    """List all dashboard versions for a dataset's history lineage."""
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
            {"id": str(d.id), "version": d.version, "created_at": d.created_at}
            for d in dashboards
        ]
    }


@router.post("/dashboard/{dataset_id}/rollback/{dashboard_id}")
async def rollback_dashboard(
    dataset_id: str, dashboard_id: str, db: AsyncSession = Depends(get_db)
) -> dict:
    """Roll back the workspace to a specific dashboard version."""
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
async def update_layout(
    dataset_id: str, layout: list[dict], db: AsyncSession = Depends(get_db)
) -> dict:
    """Auto-save: update component positions for the latest dashboard version."""
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
async def save_dashboard_version(
    dataset_id: str, layout: list[dict], db: AsyncSession = Depends(get_db)
) -> dict:
    """Create a new versioned snapshot of the dashboard with updated layout positions."""
    try:
        ds_id = uuid.UUID(dataset_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dataset ID format")

    result = await db.execute(
        select(Dashboard)
        .filter(Dashboard.dataset_id == ds_id)
        .order_by(Dashboard.version.desc())
    )
    latest_dash = result.scalars().first()

    if not latest_dash:
        raise HTTPException(status_code=404, detail="No dashboard found for this dataset")

    new_version = latest_dash.version + 1
    new_dash = Dashboard(
        dataset_id=ds_id,
        name=latest_dash.name,
        layout_json=latest_dash.layout_json,
        version=new_version,
        active_version=new_version,
    )
    db.add(new_dash)
    await db.flush()

    for item in layout:
        try:
            comp_id = uuid.UUID(item["id"])
            pos = item["position"]
            comp_result = await db.execute(
                select(DashboardComponent).filter(DashboardComponent.id == comp_id)
            )
            old_comp = comp_result.scalars().first()
            if old_comp:
                db.add(
                    DashboardComponent(
                        dashboard_id=new_dash.id,
                        query_plan=old_comp.query_plan,
                        position=pos,
                        component_type=old_comp.component_type,
                        chart_schema=old_comp.chart_schema,
                    )
                )
        except (ValueError, KeyError):
            continue

    await db.commit()

    return await get_dashboard_by_id(str(new_dash.id), db)
