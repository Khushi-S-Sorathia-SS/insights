"""
Dashboard version management and component patching.

Creates new dashboard versions by cloning existing ones, then applies
agent-generated chart schemas (new additions or in-place replacements).
"""

import uuid
from datetime import datetime
from typing import Dict, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.config.app_config import AppConfig
from src.app.db.models import Dashboard, DashboardComponent


async def create_dashboard_version(
    db: AsyncSession,
    old_dash_id: uuid.UUID,
) -> Tuple[uuid.UUID, Dict[str, str]]:
    """
    Clone an existing dashboard into a new version.

    All components are copied to the new dashboard. Returns the new dashboard's
    UUID and a mapping of old component ID → new component ID so that
    replace_id references in chart schemas can be remapped correctly.

    Parameters
    ----------
    db:
        Async database session.
    old_dash_id:
        UUID of the dashboard to clone.

    Returns
    -------
    Tuple[uuid.UUID, Dict[str, str]]
        (new_dashboard_id, {old_component_id: new_component_id})
    """
    id_mapping: Dict[str, str] = {}

    result = await db.execute(select(Dashboard).filter(Dashboard.id == old_dash_id))
    old_dash = result.scalars().first()

    if not old_dash:
        # Nothing to clone — return the original ID with an empty mapping
        return old_dash_id, id_mapping

    new_dash = Dashboard(
        dataset_id=old_dash.dataset_id,
        name=old_dash.name,
        layout_json=old_dash.layout_json,
        version=old_dash.version + 1,
        active_version=old_dash.active_version + 1,
        created_at=datetime.utcnow(),
    )
    db.add(new_dash)
    await db.flush()  # Materialise new_dash.id before cloning components

    result = await db.execute(
        select(DashboardComponent).filter(
            DashboardComponent.dashboard_id == old_dash_id
        )
    )
    old_components = result.scalars().all()

    for comp in old_components:
        new_comp = DashboardComponent(
            dashboard_id=new_dash.id,
            query_plan=comp.query_plan,
            position=comp.position,
            component_type=comp.component_type,
            chart_schema=comp.chart_schema,
        )
        db.add(new_comp)
        await db.flush()  # Materialise new_comp.id for the mapping
        id_mapping[str(comp.id)] = str(new_comp.id)

    return new_dash.id, id_mapping


async def apply_dashboard_changes(
    db: AsyncSession,
    dash_id: uuid.UUID,
    chart_schemas: list[dict],
    insight_text: str,
) -> None:
    """
    Apply agent-generated chart schemas to a dashboard.

    For each schema:
    - If it contains a `replace_id` that matches an existing component,
      update that component in-place.
    - If no match is found, try a fuzzy title match against existing components.
    - If still no match, add a new component positioned below existing ones.

    After processing charts, update or create the insight text widget.

    Parameters
    ----------
    db:
        Async database session.
    dash_id:
        UUID of the dashboard to update (should be the newly cloned version).
    chart_schemas:
        List of chart schema dicts from the agent. May contain `replace_id`.
    insight_text:
        Natural language insight text from the agent. Empty string means skip.
    """
    result = await db.execute(
        select(DashboardComponent).filter(
            DashboardComponent.dashboard_id == dash_id
        )
    )
    existing_components: Dict[str, DashboardComponent] = {
        str(c.id): c for c in result.scalars().all()
    }

    # Determine the max Y+H to know where to append new rows
    max_y = max(
        (
            comp.position.get("y", 0) + comp.position.get("h", 0)
            for comp in existing_components.values()
        ),
        default=0,
    )

    for i, schema in enumerate(chart_schemas):
        replace_id = schema.pop("replace_id", None)
        target_comp: DashboardComponent | None = None

        # 1. Direct ID match
        if replace_id and replace_id in existing_components:
            target_comp = existing_components[replace_id]
        else:
            # 2. Fuzzy title match — find an existing chart whose title shares
            #    significant words with the new schema's title
            new_title = schema.get("title", "").lower()
            if new_title:
                for c_id, comp in existing_components.items():
                    existing_title = (
                        (comp.chart_schema.get("title", "") if comp.chart_schema else "")
                        .lower()
                    )
                    if any(
                        word in existing_title
                        for word in new_title.split()
                        if len(word) > 3
                    ):
                        target_comp = comp
                        break

        if target_comp:
            # In-place replacement
            target_comp.chart_schema = schema
            target_comp.component_type = "chart"
        else:
            # New component — place in 2-column grid below existing content
            current_idx = len(existing_components) + i
            x = (current_idx % 2) * AppConfig.DEFAULT_WIDGET_WIDTH
            row_y = max_y + (i // 2) * AppConfig.DEFAULT_WIDGET_HEIGHT

            db.add(
                DashboardComponent(
                    dashboard_id=dash_id,
                    position={
                        "x": x,
                        "y": row_y,
                        "w": AppConfig.DEFAULT_WIDGET_WIDTH,
                        "h": AppConfig.DEFAULT_WIDGET_HEIGHT,
                    },
                    component_type="chart",
                    chart_schema=schema,
                )
            )

    # ── Update or create the insight widget ───────────────────────────────────
    if insight_text:
        insight_comp = next(
            (c for c in existing_components.values() if c.component_type == "insight"),
            None,
        )
        if insight_comp:
            insight_comp.chart_schema = {"content": insight_text}
        else:
            new_charts_height = ((len(chart_schemas) + 1) // 2) * AppConfig.DEFAULT_WIDGET_HEIGHT
            db.add(
                DashboardComponent(
                    dashboard_id=dash_id,
                    position={
                        "x": 0,
                        "y": max_y + new_charts_height,
                        "w": AppConfig.GRID_COLUMNS,
                        "h": AppConfig.INSIGHT_WIDGET_HEIGHT,
                    },
                    component_type="insight",
                    chart_schema={"content": insight_text},
                )
            )

    await db.commit()
