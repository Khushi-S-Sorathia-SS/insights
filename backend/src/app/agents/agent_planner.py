"""
Agent planner using Deep Agents with Azure OpenAI for generating Python analysis
code. Integrated with LangSmith for execution tracing and Daytona sandbox for
secure code execution.

Uses:
- LLM_TEMPERATURE_AGENT from settings (defaults 0.1 — slight creativity needed)
- get_agent_system_prompt() from prompts.agent_system_prompt
- HumanMessage from langchain_core.messages (structured message types)
- Proper logger for all debug/info output — no print() calls
"""

import json
import math
import re
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_openai import AzureChatOpenAI
from deepagents import HarnessProfileConfig, create_deep_agent, register_harness_profile
from langchain_daytona import DaytonaSandbox
from daytona import Daytona, DaytonaConfig

from src.app.config.settings import get_settings
from src.app.models.session import DatasetMetadata
from src.app.prompts.agent_system_prompt import get_agent_system_prompt
from src.app.utils.langsmith_tracer import trace_function
from src.app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

# ── LLM initialisation ────────────────────────────────────────────────────────
# DeepAgents is used only with Azure OpenAI in this app.
# Exclude Anthropic-specific prompt-caching middleware to avoid unrelated
# provider labels in LangSmith traces.
register_harness_profile(
    "openai",
    HarnessProfileConfig(excluded_middleware={"AnthropicPromptCachingMiddleware"}),
)
register_harness_profile(
    "azure",
    HarnessProfileConfig(excluded_middleware={"AnthropicPromptCachingMiddleware"}),
)

llm = AzureChatOpenAI(
    openai_api_type="azure",
    api_key=settings.AZURE_OPENAI_API_KEY,
    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
    azure_deployment=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
    api_version=settings.AZURE_OPENAI_API_VERSION,
    model=settings.AZURE_OPENAI_MODEL_NAME,
    temperature=settings.LLM_TEMPERATURE_AGENT,
)


def _clean_numeric_values(obj: Any) -> Any:
    """
    Recursively replace NaN and Infinity float values with None.

    PostgreSQL JSONB does not accept IEEE 754 special float values, so they
    must be sanitised before persisting chart schemas.
    """
    if isinstance(obj, dict):
        return {k: _clean_numeric_values(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean_numeric_values(item) for item in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj


def _strip_markdown_from_text(text: str) -> str:
    """Remove markdown code blocks and Daytona file paths from agent output."""
    # Strip any fenced code blocks (```python ... ```, ```json ... ```, etc.)
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL).strip()
    # Strip any stray Daytona sandbox file path references
    text = re.sub(r"/home/daytona/\S+", "", text).strip()
    return text


def _parse_json_from_sandbox(raw: str) -> list[dict]:
    """
    Parse chart schemas from the raw string downloaded from the sandbox.

    Handles the case where the LLM accidentally wrapped the JSON in markdown
    fences despite being told not to.
    """
    raw = raw.strip()
    if not raw:
        return []

    # Strip accidental markdown wrapper if present
    if "```json" in raw:
        match = re.search(r"```json\s*(.*?)\s*```", raw, re.DOTALL)
        if match:
            raw = match.group(1)
    elif "```" in raw:
        match = re.search(r"```\s*(.*?)\s*```", raw, re.DOTALL)
        if match:
            raw = match.group(1)

    return json.loads(raw)


@trace_function(name="generate_analysis_code", tags=["agent", "code_generation", "deepagents"])
def generate_analysis_code(
    user_query: str,
    dataset: DatasetMetadata,
    raw_data: bytes,
    chart_rules: str = "",
    current_widgets_summary: list[dict] | None = None,
    current_widgets_full: list[dict] | None = None,
) -> dict[str, Any]:
    """
    Generate and execute Python analysis code via Deep Agents in a Daytona sandbox.

    The agent receives the dataset as a CSV file uploaded directly to the sandbox,
    runs Python analysis code to answer the user query, and writes chart schemas
    to /home/daytona/chart_schemas.json. We then download and parse those schemas.

    Parameters
    ----------
    user_query:
        The user's natural language request.
    dataset:
        Metadata about the uploaded dataset (columns, dtypes, preview rows).
    raw_data:
        Raw CSV bytes — uploaded directly into the Daytona sandbox.
    chart_rules:
        Formatted chart schema rules from the semantic layer (injected into prompt).
    current_widgets_summary:
        Lightweight list of dashboard widget summaries for context (id, type, title).
    current_widgets_full:
        Full widget schemas uploaded to the sandbox for chart-replacement operations.

    Returns
    -------
    dict with keys:
        - "output": str — natural language response from the agent
        - "chart_schemas": list[dict] — parsed chart schema objects (may be empty)
    """
    # Initialise a fresh Daytona sandbox per request for isolation using explicit config
    daytona_config = DaytonaConfig(api_key=settings.DAYTONA_API_KEY)
    daytona_client = Daytona(config=daytona_config)
    sandbox = daytona_client.create()
    backend = DaytonaSandbox(sandbox=sandbox)

    try:
        # ── Upload data files to the sandbox ──────────────────────────────────
        sandbox_path = "/home/daytona/data.csv"
        sandbox.fs.upload_file(raw_data, sandbox_path)
        logger.debug(f"Uploaded data.csv to sandbox at {sandbox_path}")

        # Upload full widget schemas so the agent can inspect existing charts
        if current_widgets_full:
            schema_bytes = json.dumps(current_widgets_full, indent=2).encode("utf-8")
            sandbox.fs.upload_file(schema_bytes, "/home/daytona/dashboard_schemas.json")
            logger.debug(f"Uploaded dashboard_schemas.json ({len(schema_bytes)} bytes)")

        # Upload the dashboard helper script for easy schema parsing inside sandbox
        try:
            with open("src/app/utils/dashboard_helpers.py", "rb") as f:
                sandbox.fs.upload_file(f.read(), "/home/daytona/dashboard_helpers.py")
            logger.debug("Uploaded dashboard_helpers.py to sandbox")
        except FileNotFoundError:
            logger.warning("dashboard_helpers.py not found locally — skipping upload")

        # ── Build system prompt from dataset context ───────────────────────────
        system_prompt = get_agent_system_prompt(
            dataset_filename=dataset.filename,
            dataset_columns=dataset.columns,
            dataset_dtypes=dataset.dtypes,
            dataset_preview_rows=dataset.preview_rows,
            sandbox_path=sandbox_path,
            chart_rules=chart_rules,
            current_widgets_summary=current_widgets_summary,
        )

        # ── Build user message using LangChain message type ───────────────────
        user_message_content = (
            f"User Query: {user_query}\n\n"
            "IMPORTANT: You MUST use your tools to complete this task. "
            "Do NOT just describe what you would do.\n"
            "- If this is a replacement/chart change: read the existing chart schema "
            "from dashboard_schemas.json, build the new schema JSON, and write it to "
            "/home/daytona/chart_schemas.json using write_file.\n"
            "- If this is a new chart request: write Python code to analyze data.csv, "
            "compute the chart data, and write the chart schema to "
            "/home/daytona/chart_schemas.json.\n"
            "- Then provide a short natural language summary in your final response."
        )
        user_message = HumanMessage(content=user_message_content)

        # ── Create and invoke the Deep Agent ──────────────────────────────────
        agent = create_deep_agent(
            model=llm,
            system_prompt=system_prompt,
            backend=backend,
        )

        logger.info(f"Invoking Deep Agent for query: {user_query[:80]}...")
        result = agent.invoke({"messages": [user_message]})

        # ── Extract the final natural-language response ───────────────────────
        output_text = ""
        raw_content = ""

        if result and "messages" in result:
            last_message = result["messages"][-1]
            raw_content = (
                last_message.content
                if hasattr(last_message, "content")
                else str(last_message)
            )
            output_text = _strip_markdown_from_text(raw_content)

            # If the agent only output code with no prose, give a fallback message
            if not output_text and raw_content.strip():
                output_text = (
                    "Analysis code executed successfully, "
                    "but no natural language summary was provided."
                )
        else:
            output_text = "Analysis completed."

        logger.debug(f"Agent response length: {len(output_text)} chars")

        # ── Download and parse chart schemas from the sandbox ─────────────────
        chart_schemas: list[dict] = []

        try:
            logger.debug("Downloading chart_schemas.json from sandbox...")
            try:
                output_bytes = sandbox.fs.download_file("/home/daytona/chart_schemas.json")
                output_str = output_bytes.decode("utf-8")
                logger.debug(f"Downloaded {len(output_str)} chars from sandbox")
            except Exception as download_err:
                logger.warning(f"chart_schemas.json not found in sandbox: {download_err}")
                output_str = ""

            if output_str.strip():
                parsed = _parse_json_from_sandbox(output_str)
                chart_schemas = [_clean_numeric_values(chart) for chart in parsed]
                logger.info(f"Parsed {len(chart_schemas)} chart schemas from sandbox file")
            else:
                # Fallback: try to find a JSON array in the raw agent response text
                # We use raw_content here because output_text has markdown stripped
                logger.warning(
                    "No chart schemas in sandbox file — attempting fallback parse "
                    "from agent response text"
                )
                match = re.search(r"\[\s*\{.*\}\s*\]", raw_content, re.DOTALL)
                if match:
                    try:
                        chart_schemas = json.loads(match.group(0))
                        chart_schemas = [_clean_numeric_values(c) for c in chart_schemas]
                        logger.info(
                            f"Fallback: parsed {len(chart_schemas)} charts from response text"
                        )
                    except json.JSONDecodeError as parse_err:
                        logger.warning(f"Fallback JSON parse failed: {parse_err}")
                        chart_schemas = []
                else:
                    chart_schemas = []

        except Exception as schema_err:
            # Schema retrieval failure must not mask a successful analysis response
            logger.error(f"Failed to retrieve/parse chart schemas: {schema_err}")
            chart_schemas = []

        return {"output": output_text, "chart_schemas": chart_schemas}

    finally:
        # ── Sandbox cleanup ───────────────────────────────────────────────────
        # Cleanup failure is logged but NOT re-raised — the analysis already
        # succeeded at this point and we must not mask that with a cleanup error.
        try:
            sandbox.delete()
            logger.debug("Sandbox deleted successfully")
        except Exception as cleanup_err:
            logger.error(f"Sandbox cleanup failed: {cleanup_err}")
