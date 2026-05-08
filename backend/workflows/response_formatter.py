"""
Formats sandbox execution output for chat responses.
"""

from typing import Dict, Optional

from ..models.session import ChatResponse


def format_sandbox_response(output: Dict[str, object]) -> ChatResponse:
    """Transform sandbox result into a ChatResponse."""
    stdout = str(output.get("stdout", "")).strip()
    stderr = str(output.get("stderr", "")).strip()
    chart_schemas = output.get("chart_schemas", []) or []
    execution_time_ms = output.get("execution_time_ms")

    if not stdout and stderr:
        content = f"An error occurred during analysis.\n{stderr}"
    else:
        content = stdout or "Analysis completed successfully."
        if stderr:
            content += f"\n\nAdditional notes:\n{stderr}"

    chart_schema: Optional[dict] = None
    if chart_schemas:
        chart_schema = chart_schemas[0]

    return ChatResponse(
        content=content,
        chart_schema=chart_schema,
        execution_time_ms=int(execution_time_ms) if execution_time_ms is not None else None,
    )
