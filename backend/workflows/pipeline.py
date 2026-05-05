"""
Pipeline orchestration for processing chat queries.
Deep Agent analysis executes via DaytonaSandbox in backend/workflows/agent_planner.py.
Integrated with LangSmith for execution tracing.
"""

import pandas as pd
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

logger = get_logger(__name__)


@trace_function(name="process_chat_request", tags=["chat", "pipeline"])
def process_chat_request(session_id: str, user_input: str) -> ChatResponse:
    """Process a chat request and return a response with analysis."""
    session = session_manager.get_session(session_id)
    session.add_message("user", user_input)
    
    logger.info(f"Processing chat request. Session: {session_id}, Query: {user_input[:50]}...")

    if not session.dataset:
        raise SessionError("No dataset has been uploaded for this session.")

    intent = classify_intent(user_input)

    if intent == IntentType.DIRECT:
        content = _direct_response(session.dataset.file_path, user_input)
        response = ChatResponse(content=content, execution_time_ms=0)
        session.add_message("assistant", response.content)
        return response

    # generate_analysis_code now returns a dict with output and charts
    result = generate_analysis_code(user_input, session.dataset)
    output_text = result.get("output", "")
    charts = result.get("charts", [])
    
    logger.info("Generated analysis code for chat input: %s", output_text[:100])
    
    # Format the response with charts
    from ..models.session import ChatResponse
    formatted_content = output_text
    if charts:
        formatted_content += f"\n\n[{len(charts)} charts generated]"

    chart_url = None
    if charts:
        first_chart = charts[0]
        chart_url = first_chart if first_chart.startswith("data:") else f"data:image/png;base64,{first_chart}"

    response = ChatResponse(content=formatted_content, chart_url=chart_url, execution_time_ms=0)
    session.add_message(
        "assistant",
        response.content,
        analysis_result={
            "charts": charts,
            "execution_time_ms": 0,
        },
    )
    return response


def _direct_response(dataset_path: str, user_input: str) -> str:
    try:
        df = pd.read_csv(dataset_path)
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
