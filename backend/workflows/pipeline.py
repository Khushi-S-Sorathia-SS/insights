"""
Pipeline orchestration for processing chat queries (Dataset-Centric).
Deep Agent analysis executes via DaytonaSandbox in backend/workflows/agent_planner.py.
Integrated with LangSmith for execution tracing and PostgreSQL for state persistence.
"""

import pandas as pd
import io
import asyncio
from datetime import datetime
from typing import Optional
import uuid

from ..models.session import ChatResponse, DatasetMetadata
from ..workflows.agent_planner import generate_analysis_code
from ..workflows.intent_classifier import IntentType, classify_intent, parse_command, ParsedCommand
from ..workflows.nlp_query_executor import execute_nlp_query
from ..utils.error_handler import SandboxError, SessionError
from ..utils.langsmith_tracer import trace_function
from ..utils.logger import get_logger
from ..db.models import Dataset, Dashboard, DashboardComponent, ChatMessage
from .dashboard_manager import create_dashboard_version, apply_dashboard_changes
from ..semantic.semantic_layer import get_chart_rules
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = get_logger(__name__)


def find_chart_to_replace(widgets: list, source_type: str = None, target_title: str = None) -> str:
    """Find the chart to replace based on parsed command parameters."""
    if not widgets:
        return None
    
    if target_title:
        target_title_lower = target_title.lower()
        for widget in widgets:
            if widget.get("type") == "chart":
                widget_title = widget.get("title", "").lower()
                if target_title_lower in widget_title:
                    return widget["id"]
    
    if source_type:
        candidates = []
        for widget in widgets:
            if widget.get("type") == "chart":
                widget_title = widget.get("title", "").lower()
                if source_type in widget_title:
                    candidates.append(widget)
        
        if len(candidates) == 1:
            return candidates[0]["id"]
        
        if source_type == "pie":
            pie_candidates = [w for w in widgets if w.get("type") == "chart" and 
                            "distribution" in w.get("title", "").lower()]
            if len(pie_candidates) == 1:
                return pie_candidates[0]["id"]
    
    return None


@trace_function(name="process_chat_request", tags=["chat", "pipeline"])
async def process_chat_request(dataset_id: str, user_input: str, db: AsyncSession, parsed_command: dict = None) -> ChatResponse:
    """Process a chat request and return a response with analysis, using persistent state."""
    logger.info(f"Processing chat request. Dataset: {dataset_id}, Query: {user_input[:50]}...")

    try:
        ds_uuid = uuid.UUID(dataset_id)
    except ValueError:
        raise SessionError(f"Invalid dataset ID: {dataset_id}")

    # Fetch dataset metadata and raw data from DB
    result = await db.execute(select(Dataset).filter(Dataset.id == ds_uuid))
    dataset_record = result.scalars().first()
    
    if not dataset_record:
        raise SessionError("Dataset record not found in database.")
    
    raw_data = dataset_record.raw_data
    
    # Prepare metadata for the agent
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
        uploaded_at=dataset_record.uploaded_at
    )

    # Persist user message
    user_msg = ChatMessage(
        dataset_id=ds_uuid,
        role="user",
        content=user_input,
        created_at=datetime.utcnow()
    )
    db.add(user_msg)
    await db.commit()

    # Parse intent
    if parsed_command:
        intent_str = parsed_command.get("intent", "analysis")
        params = parsed_command.get("params", {})
        parsed_command_obj = ParsedCommand(IntentType(intent_str), params)
    else:
        parsed_command_obj = parse_command(user_input)
    
    intent = parsed_command_obj.intent

    # Fetch dynamic chart rules
    chart_rules = await get_chart_rules(db)

    # Fetch current dashboard components for context
    current_widgets = []
    dash_result = await db.execute(
        select(Dashboard)
        .filter(Dashboard.dataset_id == ds_uuid)
        .order_by(Dashboard.version.desc(), Dashboard.created_at.desc())
    )
    dashboard_record = dash_result.scalars().first()
    
    if dashboard_record:
        comp_result = await db.execute(select(DashboardComponent).filter(DashboardComponent.dashboard_id == dashboard_record.id))
        components = comp_result.scalars().all()
        for comp in components:
            widget = {
                "id": str(comp.id),
                "type": comp.component_type,
                "title": comp.chart_schema.get("title", "Untitled") if comp.chart_schema else "Untitled"
            }
            current_widgets.append(widget)

    # generate_analysis_code
    agent_result = await asyncio.to_thread(
        generate_analysis_code, 
        user_input, 
        metadata, 
        raw_data, 
        chart_rules,
        current_widgets
    )
    output_text = agent_result.get("output", "")
    chart_schemas = agent_result.get("chart_schemas", [])
    
    logger.info("Generated analysis for query: %s", output_text[:100])
    
    # Format the response
    formatted_content = output_text
    if chart_schemas:
        formatted_content += f"\n\n[{len(chart_schemas)} charts generated]"

    # Handle dashboard updates if needed
    new_dash_id = None
    if dashboard_record and (chart_schemas or intent == IntentType.REPLACE):
        # Use parsed command parameters for intelligent replacement
        if chart_schemas and intent == IntentType.REPLACE:
            params = parsed_command_obj.params
            for schema in chart_schemas:
                if not schema.get("replace_id"):
                    target_chart_id = find_chart_to_replace(
                        current_widgets, 
                        params.get("source_type"), 
                        params.get("target_title")
                    )
                    if target_chart_id:
                        schema["replace_id"] = target_chart_id
                        if params.get("target_type"):
                            schema["type"] = params["target_type"]
                        break

        # Versioning/Applying changes
        new_dash_id = await create_dashboard_version(db, dashboard_record.id)
        await apply_dashboard_changes(db, new_dash_id, chart_schemas, output_text)
        
        # Update dashboard metadata (tracking active version)
        dashboard_record.active_version += 1
        dashboard_record.updated_at = datetime.utcnow()

    # Persist assistant message
    assistant_msg = ChatMessage(
        dataset_id=ds_uuid,
        role="assistant",
        content=formatted_content,
        chart_schema=chart_schemas[0] if chart_schemas else None,
        execution_time_ms=0,
        created_at=datetime.utcnow()
    )
    db.add(assistant_msg)
    await db.commit()

    # Final response should point to the NEW dashboard version if changes were made
    return ChatResponse(
        content=formatted_content,
        chart_schema=chart_schemas[0] if chart_schemas else None,
        execution_time_ms=0,
        dashboard_id=str(new_dash_id) if (chart_schemas or intent == IntentType.REPLACE) else (str(dashboard_record.id) if dashboard_record else None),
        version=dashboard_record.active_version if dashboard_record else None,
    )
