"""
Dashboard route — fetch dashboard state, manage versions, handle layout updates.
"""

import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
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
    """Fetch the active dashboard version for a dataset workspace."""
    try:
        ds_id = uuid.UUID(dataset_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dataset ID format")

    # Fetch the latest dashboard to find what active_version is set to
    result = await db.execute(
        select(Dashboard)
        .filter(Dashboard.dataset_id == ds_id)
        .order_by(Dashboard.version.desc())
    )
    latest_dashboard = result.scalars().first()

    if not latest_dashboard:
        return {"widgets": [], "version": 0, "dashboard_id": None}

    # Fetch the specific dashboard version designated as active
    active_result = await db.execute(
        select(Dashboard)
        .filter(
            Dashboard.dataset_id == ds_id,
            Dashboard.version == latest_dashboard.active_version,
        )
    )
    dashboard = active_result.scalars().first()

    if not dashboard:
        # Fallback to the latest dashboard record if the active version is missing/invalid
        dashboard = latest_dashboard

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
    """Roll back the workspace to a specific dashboard version by updating the active pointer."""
    try:
        dash_id = uuid.UUID(dashboard_id)
        ds_id = uuid.UUID(dataset_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dashboard ID or dataset ID format")

    result = await db.execute(select(Dashboard).filter(Dashboard.id == dash_id))
    dashboard = result.scalars().first()

    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard version not found")

    # Update active_version on all dashboard records for this dataset
    await db.execute(
        update(Dashboard)
        .filter(Dashboard.dataset_id == ds_id)
        .values(active_version=dashboard.version)
    )
    await db.commit()

    return {"status": "success", "active_dashboard_id": str(dash_id)}


@router.post("/dashboard/{dataset_id}/layout")
async def update_layout(
    dataset_id: str, layout: list[dict], db: AsyncSession = Depends(get_db)
) -> dict:
    """Auto-save: update component positions for the active dashboard version."""
    try:
        ds_id = uuid.UUID(dataset_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dataset ID format")

    # Fetch the latest dashboard record to check active_version
    result = await db.execute(
        select(Dashboard)
        .filter(Dashboard.dataset_id == ds_id)
        .order_by(Dashboard.version.desc())
    )
    latest_dashboard = result.scalars().first()

    if not latest_dashboard:
        raise HTTPException(status_code=404, detail="No dashboard found for this dataset")

    # Fetch the active dashboard record
    active_result = await db.execute(
        select(Dashboard)
        .filter(
            Dashboard.dataset_id == ds_id,
            Dashboard.version == latest_dashboard.active_version,
        )
    )
    dashboard = active_result.scalars().first()

    if not dashboard:
        dashboard = latest_dashboard

    # If the active version is historical (older than absolute latest), perform branching clone
    is_historical = latest_dashboard.active_version < latest_dashboard.version

    if is_historical:
        new_version = latest_dashboard.version + 1
        new_dash = Dashboard(
            dataset_id=ds_id,
            name=dashboard.name,
            layout_json=dashboard.layout_json,
            version=new_version,
            active_version=new_version,
            created_at=datetime.datetime.utcnow(),
        )
        db.add(new_dash)
        await db.flush()  # Materialise new_dash.id

        # Fetch all components belonging to the historical dashboard to clone them
        comp_result = await db.execute(
            select(DashboardComponent)
            .filter(DashboardComponent.dashboard_id == dashboard.id)
        )
        old_components = comp_result.scalars().all()

        # Map new layout positions by component ID
        layout_map = {item["id"]: item["position"] for item in layout if "id" in item and "position" in item}

        new_comps = []
        for old_comp in old_components:
            old_id_str = str(old_comp.id)
            pos = layout_map.get(old_id_str, old_comp.position)

            new_comp = DashboardComponent(
                dashboard_id=new_dash.id,
                query_plan=old_comp.query_plan,
                position=pos,
                component_type=old_comp.component_type,
                chart_schema=old_comp.chart_schema,
            )
            db.add(new_comp)
            new_comps.append(new_comp)

        await db.flush()

        # Propagate the active version across all dashboard records
        await db.execute(
            update(Dashboard)
            .filter(Dashboard.dataset_id == ds_id)
            .values(active_version=new_version)
        )

        new_dash.last_layout_update = datetime.datetime.utcnow()
        await db.commit()

        # Format widgets to match direct dashboard fetch payload
        widgets = []
        for comp in new_comps:
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

        return {
            "status": "success",
            "last_updated": new_dash.last_layout_update,
            "version": new_version,
            "widgets": widgets,
            "dashboard_id": str(new_dash.id),
        }

    else:
        # Standard in-place position updates for the active latest dashboard version
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
    """Create a new versioned snapshot of the dashboard with updated layout positions based on the active one."""
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

    # Fetch the active dashboard record
    active_result = await db.execute(
        select(Dashboard)
        .filter(
            Dashboard.dataset_id == ds_id,
            Dashboard.version == latest_dash.active_version,
        )
    )
    active_dash = active_result.scalars().first()

    if not active_dash:
        active_dash = latest_dash

    new_version = latest_dash.version + 1
    new_dash = Dashboard(
        dataset_id=ds_id,
        name=active_dash.name,
        layout_json=active_dash.layout_json,
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

    # Update active_version on all dashboards for this dataset
    await db.execute(
        update(Dashboard)
        .filter(Dashboard.dataset_id == ds_id)
        .values(active_version=new_version)
    )
    await db.commit()

    return await get_dashboard_by_id(str(new_dash.id), db)
