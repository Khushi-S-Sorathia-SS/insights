"""
Pipeline orchestration for processing chat queries (Dataset-Centric).

Thin orchestrator — classifies intent and routes to:
- execute_nlp_query() for DIRECT intents (local pandas, no sandbox)
- generate_analysis_code() for all other intents (Daytona sandbox)

Dashboard versioning and persistence happen here after analysis completes.
"""

import asyncio
import io
import uuid
from datetime import datetime
from typing import Optional

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.agents.agent_planner import generate_analysis_code
from src.app.db.models import ChatMessage, Dashboard, DashboardComponent, Dataset
from src.app.models.session import ChatResponse, DatasetMetadata
from src.app.semantic.semantic_layer import get_chart_rules
from src.app.utils.error_handler import SandboxError, SessionError
from src.app.utils.langsmith_tracer import trace_function
from src.app.utils.logger import get_logger
from src.app.workflows.dashboard_manager import apply_dashboard_changes, create_dashboard_version
from src.app.workflows.intent_classifier import (
    IntentType,
    ParsedCommand,
    parse_command,
)
from src.app.workflows.nlp_query_executor import execute_nlp_query

logger = get_logger(__name__)


@trace_function(name="process_chat_request", tags=["chat", "pipeline"])
async def process_chat_request(
    dataset_id: str,
    user_input: str,
    db: AsyncSession,
    parsed_command: Optional[dict] = None,
) -> ChatResponse:
    """
    Process a chat request and return a response.

    Fetches the dataset from DB, classifies intent, routes to the appropriate
    executor, updates the dashboard if charts were generated, and persists the
    conversation turn.

    Parameters
    ----------
    dataset_id:
        UUID string of the dataset (doubles as session identifier).
    user_input:
        The user's natural language message.
    db:
        Async database session.
    parsed_command:
        Optional pre-parsed command dict from the frontend (intent + params).
        If provided, skips the LLM-based intent classification.

    Returns
    -------
    ChatResponse
        Contains the text response, optional chart schema, dashboard ID, and version.
    """
    logger.info(
        f"Processing chat request — dataset: {dataset_id}, "
        f"query: {user_input[:60]!r}"
    )

    try:
        ds_uuid = uuid.UUID(dataset_id)
    except ValueError:
        raise SessionError(f"Invalid dataset ID: {dataset_id}")

    # ── Fetch dataset record ───────────────────────────────────────────────────
    result = await db.execute(select(Dataset).filter(Dataset.id == ds_uuid))
    dataset_record = result.scalars().first()

    if not dataset_record:
        raise SessionError("Dataset record not found in database.")

    raw_data = dataset_record.raw_data

    metadata = DatasetMetadata(
        filename=dataset_record.filename,
        dataset_id=str(dataset_record.id),
        file_path="",
        rows=dataset_record.schema_json.get("rows", 0),
        columns=dataset_record.schema_json.get("columns", []),
        dtypes=dataset_record.schema_json.get("dtypes", {}),
        missing_values=dataset_record.schema_json.get("missing_values", {}),
        preview_rows=dataset_record.schema_json.get("preview_rows", []),
        size_bytes=len(raw_data),
        uploaded_at=dataset_record.uploaded_at,
    )

    # ── Persist user message ───────────────────────────────────────────────────
    user_msg = ChatMessage(
        dataset_id=ds_uuid,
        role="user",
        content=user_input,
        created_at=datetime.utcnow(),
    )
    db.add(user_msg)
    await db.commit()

    # ── Determine intent ───────────────────────────────────────────────────────
    if parsed_command:
        # Frontend provided a pre-classified command — use it directly
        intent_str = parsed_command.get("intent", "analysis")
        params = parsed_command.get("params", {})
        command_obj = ParsedCommand(intent=IntentType(intent_str), params=params)
    else:
        command_obj = parse_command(user_input)

    intent = command_obj.intent
    logger.info(f"Classified intent: {intent}")

    # ── Fetch chart rules and current dashboard context ───────────────────────
    chart_rules = await get_chart_rules(db)

    current_widgets_summary: list[dict] = []
    current_widgets_full: list[dict] = []
    dashboard_record: Optional[Dashboard] = None

    dash_result = await db.execute(
        select(Dashboard)
        .filter(Dashboard.dataset_id == ds_uuid)
        .order_by(Dashboard.version.desc(), Dashboard.created_at.desc())
    )
    dashboard_record = dash_result.scalars().first()

    if dashboard_record:
        comp_result = await db.execute(
            select(DashboardComponent).filter(
                DashboardComponent.dashboard_id == dashboard_record.id
            )
        )
        components = comp_result.scalars().all()

        for comp in components:
            current_widgets_full.append(
                {
                    "id": str(comp.id),
                    "component_type": comp.component_type,
                    "schema": comp.chart_schema,
                }
            )
            current_widgets_summary.append(
                {
                    "id": str(comp.id),
                    "component_type": comp.component_type,
                    "title": (
                        comp.chart_schema.get("title", "Untitled")
                        if comp.chart_schema
                        else "Untitled"
                    ),
                }
            )

    # ── Route to executor ─────────────────────────────────────────────────────
    if intent == IntentType.DIRECT:
        logger.info("Routing to lightweight NLP executor (no sandbox)")
        try:
            df = pd.read_csv(io.BytesIO(raw_data))
            output_text = execute_nlp_query(user_input, df)
            chart_schemas: list[dict] = []
        except Exception as nlp_err:
            logger.error(f"Lightweight executor failed: {nlp_err}")
            output_text = (
                f"I encountered an error analyzing the data locally: {nlp_err}"
            )
            chart_schemas = []
    else:
        logger.info(f"Routing to Deep Agent sandbox (intent: {intent})")
        agent_result = await asyncio.to_thread(
            generate_analysis_code,
            user_input,
            metadata,
            raw_data,
            chart_rules,
            current_widgets_summary,
            current_widgets_full,
        )
        output_text = agent_result.get("output", "")
        chart_schemas = agent_result.get("chart_schemas", [])

    # ── Enforce no-chart rule for DIRECT and DATA_QUERY ───────────────────────
    if intent in (IntentType.DIRECT, IntentType.DATA_QUERY):
        chart_schemas = []

    logger.info(
        f"Analysis complete — output: {len(output_text)} chars, "
        f"charts: {len(chart_schemas)}"
    )

    formatted_content = output_text
    if chart_schemas:
        formatted_content += f"\n\n[{len(chart_schemas)} charts generated]"

    # ── Update dashboard if charts were produced ──────────────────────────────
    new_dash_id: Optional[uuid.UUID] = None

    if dashboard_record and chart_schemas:
        new_dash_id, id_mapping = await create_dashboard_version(
            db, dashboard_record.id
        )

        # Remap replace_id from the old component to the cloned component ID
        for schema in chart_schemas:
            old_id = schema.get("replace_id")
            if old_id and old_id in id_mapping:
                schema["replace_id"] = id_mapping[old_id]

        await apply_dashboard_changes(db, new_dash_id, chart_schemas, output_text)

        dashboard_record.active_version += 1
        dashboard_record.updated_at = datetime.utcnow()

    # ── Persist assistant message ──────────────────────────────────────────────
    assistant_msg = ChatMessage(
        dataset_id=ds_uuid,
        role="assistant",
        content=formatted_content,
        chart_schema=chart_schemas[0] if chart_schemas else None,
        execution_time_ms=0,
        created_at=datetime.utcnow(),
    )
    db.add(assistant_msg)
    await db.commit()

    # ── Build and return response ─────────────────────────────────────────────
    # Point to the NEW dashboard version if changes were made
    response_dashboard_id: Optional[str] = None
    if chart_schemas or intent == IntentType.REPLACE:
        response_dashboard_id = str(new_dash_id) if new_dash_id else None
    elif dashboard_record:
        response_dashboard_id = str(dashboard_record.id)

    return ChatResponse(
        content=formatted_content,
        chart_schema=chart_schemas[0] if chart_schemas else None,
        execution_time_ms=0,
        dashboard_id=response_dashboard_id,
        version=dashboard_record.active_version if dashboard_record else None,
    )
