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


# Logic for chart replacement and modification has been moved to the Deep Agent reasoning layer.
# pipeline.py serves as a thin orchestrator.


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
    current_widgets_summary = []
    current_widgets_full = []
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
            # Full raw schema for the sandbox helper
            widget_full = {
                "id": str(comp.id),
                "component_type": comp.component_type,
                "schema": comp.chart_schema
            }
            current_widgets_full.append(widget_full)
            
            # Lightweight summary for the prompt
            widget_summary = {
                "id": str(comp.id),
                "component_type": comp.component_type,
                "title": comp.chart_schema.get("title", "Untitled") if comp.chart_schema else "Untitled"
            }
            current_widgets_summary.append(widget_summary)

    # Route based on intent: Lightweight for 'direct', Sandbox for everything else
    if intent == IntentType.DIRECT:
        logger.info("Routing to Lightweight NLP Executor (No Sandbox)")
        try:
            # Execute locally using pandas for efficiency
            df = pd.read_csv(io.BytesIO(raw_data))
            output_text = execute_nlp_query(user_input, df)
            chart_schemas = [] # Strictly no charts for direct queries
        except Exception as e:
            logger.error(f"Lightweight executor failed: {e}")
            output_text = f"I encountered an error analyzing the data locally: {str(e)}"
            chart_schemas = []
    else:
        logger.info(f"Routing to Deep Agent Sandbox (Intent: {intent})")
        # generate_analysis_code (Sandbox Path)
        agent_result = await asyncio.to_thread(
            generate_analysis_code, 
            user_input, 
            metadata, 
            raw_data, 
            chart_rules,
            current_widgets_summary,
            current_widgets_full
        )
        output_text = agent_result.get("output", "")
        chart_schemas = agent_result.get("chart_schemas", [])
    
    logger.info("Generated analysis for query: %s", output_text[:100])
    
    # Format the response
    formatted_content = output_text
    
    # Strictly enforce Graph Prevention for DIRECT and DATA_QUERY intents
    if intent in [IntentType.DIRECT, IntentType.DATA_QUERY]:
        chart_schemas = []
    
    if chart_schemas:
        formatted_content += f"\n\n[{len(chart_schemas)} charts generated]"

    # Handle dashboard updates if needed
    new_dash_id = None
    if dashboard_record and chart_schemas:
        # Use parsed command parameters for intelligent replacement
        # Versioning/Applying changes
        new_dash_id, id_mapping = await create_dashboard_version(db, dashboard_record.id)
        
        # Map old replace_id (identified by the Agent) to the new cloned component ID
        if chart_schemas:
            for schema in chart_schemas:
                old_id = schema.get("replace_id")
                if old_id and old_id in id_mapping:
                    schema["replace_id"] = id_mapping[old_id]
                    
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
