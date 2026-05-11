"""
Pipeline orchestration for processing chat queries.
Deep Agent analysis executes via DaytonaSandbox in backend/workflows/agent_planner.py.
Integrated with LangSmith for execution tracing.
"""

import pandas as pd
import io
import asyncio
from datetime import datetime
from typing import Optional

from ..models.session import ChatResponse
from ..storage.session_manager import session_manager
from ..workflows.agent_planner import generate_analysis_code
from ..workflows.intent_classifier import IntentType, classify_intent, parse_command, ParsedCommand
from ..workflows.response_formatter import format_sandbox_response
from ..utils.error_handler import SandboxError, SessionError
from ..utils.langsmith_tracer import trace_function, create_run_context
from ..utils.logger import get_logger
from ..db.models import Dataset, DashboardComponent
from .dashboard_manager import create_dashboard_version, apply_dashboard_changes
import uuid
from ..semantic.semantic_layer import get_chart_rules
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = get_logger(__name__)


def find_chart_to_replace(widgets: list, source_type: str = None, target_title: str = None) -> str:
    """Find the chart to replace based on parsed command parameters."""
    if not widgets:
        return None
    
    # If a specific title is mentioned, try to match it
    if target_title:
        target_title_lower = target_title.lower()
        for widget in widgets:
            if widget.get("type") == "chart":
                widget_title = widget.get("title", "").lower()
                if target_title_lower in widget_title:
                    return widget["id"]
    
    # If a source chart type is specified, find charts of that type
    if source_type:
        candidates = []
        for widget in widgets:
            if widget.get("type") == "chart":
                # Check if the widget title contains the source type
                widget_title = widget.get("title", "").lower()
                if source_type in widget_title:
                    candidates.append(widget)
        
        # If only one candidate matches, return it
        if len(candidates) == 1:
            return candidates[0]["id"]
        
        # For pie charts, also check for "distribution" in title
        if source_type == "pie":
            pie_candidates = [w for w in widgets if w.get("type") == "chart" and 
                            "distribution" in w.get("title", "").lower()]
            if len(pie_candidates) == 1:
                return pie_candidates[0]["id"]
    
    return None


@trace_function(name="process_chat_request", tags=["chat", "pipeline"])
async def process_chat_request(session_id: str, user_input: str, db: AsyncSession, parsed_command: dict = None) -> ChatResponse:
    """Process a chat request and return a response with analysis."""
    session = session_manager.get_session(session_id)
    session.add_message("user", user_input)
    
    logger.info(f"Processing chat request. Session: {session_id}, Query: {user_input[:50]}...")

    if not session.dataset:
        raise SessionError("No dataset has been uploaded for this session.")

    # Fetch raw data from DB
    dataset_id = session.dataset.dataset_id
    result = await db.execute(select(Dataset).filter(Dataset.id == dataset_id))
    dataset_record = result.scalars().first()
    
    if not dataset_record:
        raise SessionError("Dataset record not found in database.")
    
    raw_data = dataset_record.raw_data

    # Use provided parsed command or parse it using LangGraph
    if parsed_command:
        # Convert dict to ParsedCommand object
        intent_str = parsed_command.get("intent", "analysis")
        params = parsed_command.get("params", {})
        parsed_command_obj = ParsedCommand(IntentType(intent_str), params)
    else:
        parsed_command_obj = parse_command(user_input)
    
    intent = parsed_command_obj.intent

    if intent == IntentType.DIRECT:
        content = _direct_response(raw_data, user_input)
        response = ChatResponse(content=content, execution_time_ms=0)
        session.add_message("assistant", response.content)
        return response

    # Fetch dynamic chart rules from the Semantic Layer
    chart_rules = await get_chart_rules(db)

    # Fetch current dashboard components for context
    current_widgets = []
    dashboard_id_str = session.metadata.get("dashboard_id")
    if dashboard_id_str:
        dash_id = uuid.UUID(dashboard_id_str)
        result = await db.execute(select(DashboardComponent).filter(DashboardComponent.dashboard_id == dash_id))
        components = result.scalars().all()
        for comp in components:
            widget = {
                "id": str(comp.id),
                "type": comp.component_type,
                "title": comp.chart_schema.get("title", "Untitled") if comp.chart_schema else "Untitled"
            }
            current_widgets.append(widget)

    # generate_analysis_code now returns a dict with output and chart_schemas
    result = await asyncio.to_thread(
        generate_analysis_code, 
        user_input, 
        session.dataset, 
        raw_data, 
        chart_rules,
        current_widgets
    )
    output_text = result.get("output", "")
    chart_schemas = result.get("chart_schemas", [])
    
    logger.info("Generated analysis code for chat input: %s", output_text[:100])
    
    # Format the response with chart schemas
    formatted_content = output_text
    if chart_schemas:
        formatted_content += f"\n\n[{len(chart_schemas)} charts generated]"

    chart_schema = None
    if chart_schemas:
        chart_schema = chart_schemas[0]

    # Save to dashboard_components if dashboard_id exists
    dashboard_id_str = session.metadata.get("dashboard_id")
    if dashboard_id_str and (chart_schemas or intent == IntentType.REPLACE):
        dash_id = uuid.UUID(dashboard_id_str)

        # Use parsed command parameters for intelligent replacement
        if chart_schemas and intent == IntentType.REPLACE:
            params = parsed_command_obj.params
            
            for schema in chart_schemas:
                if not schema.get("replace_id"):
                    # Use parsed parameters to find the target chart
                    target_chart_id = find_chart_to_replace(
                        current_widgets, 
                        params.get("source_type"), 
                        params.get("target_title")
                    )
                    
                    if target_chart_id:
                        schema["replace_id"] = target_chart_id
                        # Update the schema to use the target chart type
                        if params.get("target_type"):
                            schema["type"] = params["target_type"]
                        break

        # 1. Create a new version (clone)
        new_dash_id = await create_dashboard_version(db, dash_id)
        
        # 2. Apply changes to the new version
        await apply_dashboard_changes(db, new_dash_id, chart_schemas, output_text)
        
        # 3. Update session metadata with the new dashboard ID
        session.metadata["dashboard_id"] = str(new_dash_id)
        session_manager.save_session(session)

    response = ChatResponse(
        content=formatted_content,
        chart_schema=chart_schema,
        execution_time_ms=0,
        dashboard_id=session.metadata.get("dashboard_id"),
        version=None,
    )
    session.add_message(
        "assistant",
        response.content,
        analysis_result={
            "chart_schemas": chart_schemas,
            "execution_time_ms": 0,
        },
    )
    return response


def _direct_response(raw_data: bytes, user_input: str) -> str:
    try:
        df = pd.read_csv(io.BytesIO(raw_data))
    except Exception as exc:
        return f"Unable to load dataset for analysis: {exc}"

    message = user_input.lower()

    if "missing" in message:
        missing = df.isna().sum()
        missing = missing[missing > 0]
        if missing.empty:
            return "No missing values were found in the dataset."
        lines = [f"{column}: {int(count)}" for column, count in missing.items()]
        return "Missing values by column:\n" + "\n".join(lines)

    if "duplicate" in message or "duplicates" in message:
        duplicate_rows = df[df.duplicated(keep=False)]
        count = len(duplicate_rows)
        return f"Duplicate row count: {count}."

    if "summary" in message or "analyze" in message or "insights" in message:
        return _dataset_summary(df)

    if "count" in message or "how many" in message:
        total = len(df)
        return f"The dataset contains {total} rows."

    return _dataset_summary(df)


def _dataset_summary(df: pd.DataFrame) -> str:
    numeric = df.select_dtypes(include=["number"])
    total_rows = len(df)
    total_columns = len(df.columns)
    lines = [f"Total rows: {total_rows}", f"Total columns: {total_columns}"]

    if not numeric.empty:
        numeric_summary = numeric.describe().transpose()
        for column in numeric_summary.index[:5]:
            row = numeric_summary.loc[column]
            lines.append(
                f"{column}: mean={row['mean']:.2f}, min={row['min']:.2f}, max={row['max']:.2f}"
            )
    else:
        lines.append("No numeric columns available for summary.")

    missing = df.isna().sum()
    missing_count = int(missing.sum())
    if missing_count > 0:
        lines.append(f"Missing values total: {missing_count}")

    top_columns = [col for col in df.columns if df[col].dtype == object][:3]
    for column in top_columns:
        top_value = df[column].value_counts().idxmax()
        lines.append(f"Most common {column}: {top_value}")

    return "Dataset summary:\n" + "\n".join(lines)
