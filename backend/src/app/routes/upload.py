"""
Upload route — CSV dataset ingestion and initial dashboard creation.

On upload:
1. Validates display_name uniqueness.
2. Saves the CSV via FileManager.
3. Runs the Deep Agent to generate initial charts and insights.
4. Persists the dashboard and its components to PostgreSQL.
5. Returns the dashboard ID and metadata to the frontend.

Uses AppConfig constants for all grid layout values — no magic numbers.
Uses logger for all debug/info/error output — no print() calls.
Uses INITIAL_ANALYSIS_PROMPT from prompts.agent_system_prompt.
"""

import asyncio
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.config.app_config import AppConfig
from src.app.db.database import get_db
from src.app.db.models import ChatMessage, Dashboard, DashboardComponent, Dataset
from src.app.models.session import UploadResponse
from src.app.prompts.agent_system_prompt import INITIAL_ANALYSIS_PROMPT
from src.app.semantic.semantic_layer import get_chart_rules
from src.app.storage.file_manager import file_manager
from src.app.utils.error_handler import SandboxError
from src.app.utils.logger import get_logger
from src.app.agents.agent_planner import generate_analysis_code

logger = get_logger(__name__)
router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_csv(
    file: UploadFile = File(...),
    display_name: str = Form(...),
    db: AsyncSession = Depends(get_db),
) -> UploadResponse:
    """
    Ingest a CSV dataset and bootstrap the workspace dashboard.

    The display_name must be unique across all workspaces — it is the primary
    human-readable identifier shown in the dataset selector.
    """
    # ── Validate display_name uniqueness ──────────────────────────────────────
    existing = await db.execute(
        select(Dataset).filter(Dataset.display_name == display_name)
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=400,
            detail=(
                f"Workspace name '{display_name}' already exists. "
                "Please choose a different name."
            ),
        )

    # ── Save the CSV and extract metadata ─────────────────────────────────────
    temp_session_id = f"sess_{uuid.uuid4().hex}"
    metadata = await file_manager.save_uploaded_csv(
        file, temp_session_id, db, display_name=display_name
    )
    dataset_id = metadata.dataset_id
    logger.info(f"Dataset saved: id={dataset_id} display_name={display_name!r}")

    # ── Re-read raw bytes for the agent (file pointer was consumed above) ──────
    file.file.seek(0)
    raw_data = file.file.read()

    # ── Fetch chart schema rules from the semantic layer ──────────────────────
    chart_rules = await get_chart_rules(db)

    # ── Run initial analysis via the Deep Agent ───────────────────────────────
    default_chart_schemas: list[dict] = []
    auto_insights: str = ""

    try:
        logger.info(f"Starting initial analysis for dataset {dataset_id}...")
        result = await asyncio.to_thread(
            generate_analysis_code,
            INITIAL_ANALYSIS_PROMPT,
            metadata,
            raw_data,
            chart_rules,
        )
        auto_insights = result.get("output", "Could not generate initial dataset insights.")
        default_chart_schemas = result.get("chart_schemas", [])
        logger.info(
            f"Initial analysis complete — "
            f"insights: {len(auto_insights)} chars, "
            f"charts: {len(default_chart_schemas)}"
        )
    except SandboxError as sandbox_err:
        logger.error(f"Sandbox error during initial analysis: {sandbox_err}")
        default_chart_schemas = []
        auto_insights = "Could not generate initial dataset insights."
    except Exception as unexpected_err:
        logger.error(f"Unexpected error during initial analysis: {unexpected_err}")
        default_chart_schemas = []
        auto_insights = "Could not generate initial dataset insights."

    # ── Persist the dashboard and its components ──────────────────────────────
    ds_uuid = uuid.UUID(dataset_id)

    dashboard = Dashboard(
        dataset_id=ds_uuid,
        name=f"Workspace: {metadata.filename}",
        layout_json={},
    )
    db.add(dashboard)
    await db.commit()
    await db.refresh(dashboard)
    logger.info(f"Dashboard created: id={dashboard.id}")

    # ── Persist the initial assistant chat message ────────────────────────────
    initial_msg = ChatMessage(
        dataset_id=ds_uuid,
        role="assistant",
        content=(
            f"Ingestion complete. Dataset '{metadata.filename}' has been indexed "
            "and workspace established. I am ready for advanced analytical queries."
        ),
        created_at=datetime.utcnow(),
    )
    db.add(initial_msg)

    # ── Add chart components with grid positions ──────────────────────────────
    # Layout: 2-column grid, each component gets half the grid width by default.
    # The agent may override w/h in the schema; we use AppConfig fallbacks.
    for i, schema in enumerate(default_chart_schemas):
        w = schema.get("w", AppConfig.DEFAULT_WIDGET_WIDTH)
        h = schema.get("h", AppConfig.DEFAULT_WIDGET_HEIGHT)

        # 2-column layout: alternate x=0 and x=DEFAULT_WIDGET_WIDTH
        x = (i % 2) * AppConfig.DEFAULT_WIDGET_WIDTH
        # Advance y by DEFAULT_WIDGET_HEIGHT for every new row (every 2 items)
        y = (i // 2) * AppConfig.DEFAULT_WIDGET_HEIGHT

        component = DashboardComponent(
            dashboard_id=dashboard.id,
            position={"x": x, "y": y, "w": w, "h": h},
            component_type="chart",
            chart_schema=schema,
        )
        db.add(component)

    # ── Add insight text widget below all charts ──────────────────────────────
    if auto_insights:
        # Calculate the Y position just below the last row of chart components
        chart_rows = (len(default_chart_schemas) + 1) // 2
        final_y = chart_rows * AppConfig.DEFAULT_WIDGET_HEIGHT

        insight_component = DashboardComponent(
            dashboard_id=dashboard.id,
            position={
                "x": 0,
                "y": final_y,
                "w": AppConfig.GRID_COLUMNS,
                "h": AppConfig.INSIGHT_WIDGET_HEIGHT,
            },
            component_type="insight",
            chart_schema={"content": auto_insights},
        )
        db.add(insight_component)

    # Single commit for all components and the initial message
    await db.commit()
    logger.info(
        f"Dashboard components persisted: "
        f"{len(default_chart_schemas)} charts + 1 insight"
    )

    return UploadResponse(
        session_id=dataset_id,  # dataset_id is the primary session identifier
        dashboard_id=str(dashboard.id),
        message="Upload successful",
        metadata=metadata,
        default_chart_schemas=default_chart_schemas,
        auto_insights=auto_insights,
    )
