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
from ..workflows.intent_classifier import IntentType, classify_intent
from ..workflows.response_formatter import format_sandbox_response
from ..utils.error_handler import SandboxError, SessionError
from ..utils.langsmith_tracer import trace_function, create_run_context
from ..utils.logger import get_logger
from ..db.models import Dataset
from ..semantic.semantic_layer import get_chart_rules
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = get_logger(__name__)


@trace_function(name="process_chat_request", tags=["chat", "pipeline"])
async def process_chat_request(session_id: str, user_input: str, db: AsyncSession) -> ChatResponse:
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

    intent = classify_intent(user_input)

    if intent == IntentType.DIRECT:
        content = _direct_response(raw_data, user_input)
        response = ChatResponse(content=content, execution_time_ms=0)
        session.add_message("assistant", response.content)
        return response

    # Fetch dynamic chart rules from the Semantic Layer
    chart_rules = await get_chart_rules(db)

    # generate_analysis_code now returns a dict with output and chart_schemas
    result = await asyncio.to_thread(
        generate_analysis_code, 
        user_input, 
        session.dataset, 
        raw_data, 
        chart_rules
    )
    output_text = result.get("output", "")
    chart_schemas = result.get("chart_schemas", [])
    
    logger.info("Generated analysis code for chat input: %s", output_text[:100])
    
    # Format the response with chart schemas
    from ..models.session import ChatResponse
    formatted_content = output_text
    if chart_schemas:
        formatted_content += f"\n\n[{len(chart_schemas)} charts generated]"

    chart_schema = None
    if chart_schemas:
        chart_schema = chart_schemas[0]

    # Save to dashboard_components if dashboard_id exists
    dashboard_id_str = session.metadata.get("dashboard_id")
    if dashboard_id_str:
        from ..db.models import DashboardComponent
        import uuid
        dash_id = uuid.UUID(dashboard_id_str)
        
        # We can just append to the dashboard. Let's find max position Y or just append
        for i, schema in enumerate(chart_schemas):
            component = DashboardComponent(
                dashboard_id=dash_id,
                position={"x": i % 2, "y": 100 + i, "w": 1, "h": 1}, # simple offset
                component_type="chart",
                chart_schema=schema
            )
            db.add(component)
            
        insight_component = DashboardComponent(
            dashboard_id=dash_id,
            position={"x": 0, "y": 100 + len(chart_schemas), "w": 2, "h": 1},
            component_type="insight",
            chart_schema={"content": output_text}
        )
        db.add(insight_component)
        await db.commit()

    response = ChatResponse(content=formatted_content, chart_schema=chart_schema, execution_time_ms=0)
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
