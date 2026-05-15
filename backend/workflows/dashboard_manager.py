"""
Utility for managing dashboard versions and components.
"""

import uuid
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..db.models import Dashboard, DashboardComponent

from typing import Tuple, Dict

async def create_dashboard_version(db: AsyncSession, old_dash_id: uuid.UUID) -> Tuple[uuid.UUID, Dict[str, str]]:
    """
    Creates a new version of the dashboard by cloning the existing one.
    Returns the new dashboard ID and a mapping of old component IDs to new component IDs.
    """
    id_mapping = {}
    
    # Get old dashboard
    result = await db.execute(select(Dashboard).filter(Dashboard.id == old_dash_id))
    old_dash = result.scalars().first()
    if not old_dash:
        return old_dash_id, id_mapping

    # Create new dashboard record
    new_dash = Dashboard(
        dataset_id=old_dash.dataset_id,
        name=old_dash.name,
        layout_json=old_dash.layout_json,
        version=old_dash.version + 1,
        active_version=old_dash.active_version + 1,
        created_at=datetime.utcnow()
    )
    db.add(new_dash)
    await db.flush() # Get new_dash.id

    # Clone components
    result = await db.execute(select(DashboardComponent).filter(DashboardComponent.dashboard_id == old_dash_id))
    old_components = result.scalars().all()
    for comp in old_components:
        new_comp = DashboardComponent(
            dashboard_id=new_dash.id,
            query_plan=comp.query_plan,
            position=comp.position,
            component_type=comp.component_type,
            chart_schema=comp.chart_schema
        )
        db.add(new_comp)
        await db.flush() # flush to get new_comp.id
        id_mapping[str(comp.id)] = str(new_comp.id)

    return new_dash.id, id_mapping

async def apply_dashboard_changes(
    db: AsyncSession, 
    dash_id: uuid.UUID, 
    chart_schemas: list[dict], 
    insight_text: str
) -> None:
    """
    Applies changes to the dashboard. 
    Handles replacement if 'replace_id' is present in schema.
    """
    # Find existing components to potentially replace
    result = await db.execute(select(DashboardComponent).filter(DashboardComponent.dashboard_id == dash_id))
    existing_components = {str(c.id): c for c in result.scalars().all()}

    # Track max Y to append new ones (y + h)
    max_y = 0
    for comp in existing_components.values():
        y = comp.position.get("y", 0)
        h = comp.position.get("h", 0)
        if y + h > max_y:
            max_y = y + h

    # Process each chart schema
    for i, schema in enumerate(chart_schemas):
        replace_id = schema.pop("replace_id", None)
        
        # LOGIC FIX: If intent is clearly replace but ID is missing, find the most likely target
        target_comp = None
        if replace_id and replace_id in existing_components:
            target_comp = existing_components[replace_id]
        else:
            # Match by title keywords (e.g. "gender" in "Gender Distribution")
            new_title = schema.get("title", "").lower()
            if new_title:
                for c_id, c in existing_components.items():
                    c_title = (c.chart_schema.get("title", "") if c.chart_schema else "").lower()
                    if any(word in c_title for word in new_title.split() if len(word) > 3):
                        target_comp = c
                        break
        
        if target_comp:
            # Replace existing component
            target_comp.chart_schema = schema
            target_comp.component_type = "chart"
        else:
            # Add new component
            # Calculate grid position: alternate x=0 and x=6
            current_idx = len(existing_components) + i
            x = (current_idx % 2) * 6
            # Increment y only when we start a new row
            row_y = max_y + (i // 2) * 4
            
            new_comp = DashboardComponent(
                dashboard_id=dash_id,
                position={"x": x, "y": row_y, "w": 6, "h": 4},
                component_type="chart",
                chart_schema=schema
            )
            db.add(new_comp)

    # Always update an insight component if text is provided
    if insight_text:
        # Check if there's already an insight component to update
        insight_comp = next((c for c in existing_components.values() if c.component_type == "insight"), None)
        if insight_comp:
            insight_comp.chart_schema = {"content": insight_text}
        else:
            # Place insight below newly added charts
            new_charts_height = ((len(chart_schemas) + 1) // 2) * 4
            new_insight = DashboardComponent(
                dashboard_id=dash_id,
                position={"x": 0, "y": max_y + new_charts_height, "w": 12, "h": 2},
                component_type="insight",
                chart_schema={"content": insight_text}
            )
            db.add(new_insight)

    await db.commit()
