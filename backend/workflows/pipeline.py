"""
Pipeline orchestration for processing chat queries.
"""

import pandas as pd
from datetime import datetime
from typing import Optional

from ..models.session import ChatResponse
from ..storage.session_manager import session_manager
from ..sandbox.executor import run_code_in_sandbox
from ..workflows.agent_planner import generate_analysis_code
from ..workflows.intent_classifier import IntentType, classify_intent
from ..workflows.response_formatter import format_sandbox_response
from ..utils.error_handler import SandboxError, SessionError


def process_chat_request(session_id: str, user_input: str) -> ChatResponse:
    session = session_manager.get_session(session_id)
    session.add_message("user", user_input)

    if not session.dataset:
        raise SessionError("No dataset has been uploaded for this session.")

    intent = classify_intent(user_input)

    if intent == IntentType.DIRECT:
        content = _direct_response(session.dataset.file_path, user_input)
        response = ChatResponse(content=content, execution_time_ms=0)
        session.add_message("assistant", response.content)
        return response

    code = generate_analysis_code(user_input, session.dataset)
    sandbox_output = run_code_in_sandbox(code, session.session_id, session.dataset.file_path)
    response = format_sandbox_response(sandbox_output)
    session.add_message(
        "assistant",
        response.content,
        analysis_result={
            "chart_url": response.chart_url,
            "execution_time_ms": response.execution_time_ms,
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
