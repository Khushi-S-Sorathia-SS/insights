"""
Intent classification for user queries using LangGraph.

Uses:
- PydanticOutputParser so the LLM output is parsed directly into ParsedCommand
- ParsedCommand is a Pydantic BaseModel (replaces the old plain class)
- LLM_TEMPERATURE_CLASSIFIER from settings (deterministic: 0.0)
- AppConfig for chart type variants and keyword lists
- INTENT_PROMPT from prompts.intent_classification
- get_settings() — never Settings() directly
- logger throughout — no print() calls
"""

from enum import Enum
from typing import Any, Dict, Optional

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from src.app.config.app_config import AppConfig
from src.app.config.settings import get_settings
from src.app.prompts.intent_classification import INTENT_PROMPT
from src.app.utils.langsmith_tracer import trace_function
from src.app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


# ── Domain enums ──────────────────────────────────────────────────────────────

class IntentType(str, Enum):
    DIRECT = "direct"
    DATA_QUERY = "data_query"
    ANALYSIS = "analysis"
    REPLACE = "replace"
    CREATE = "create"
    MODIFY = "modify"


# ── Pydantic output model ─────────────────────────────────────────────────────

class ParsedCommand(BaseModel):
    """Structured command parsed from a user message.

    This is both the LLM output schema (used by PydanticOutputParser) and the
    object passed through pipeline.py for intent routing.
    """

    intent: IntentType = Field(
        ...,
        description=(
            "Classified intent: one of direct, data_query, analysis, "
            "replace, create, modify"
        ),
    )
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Intent-specific parameters (chart_type, source_type, etc.)",
    )


# ── LLM initialisation ────────────────────────────────────────────────────────

llm = AzureChatOpenAI(
    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
    azure_deployment=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
    api_version=settings.AZURE_OPENAI_API_VERSION,
    api_key=settings.AZURE_OPENAI_API_KEY,
    temperature=settings.LLM_TEMPERATURE_CLASSIFIER,
)

# PydanticOutputParser automatically injects format_instructions into the prompt
intent_parser = PydanticOutputParser(pydantic_object=ParsedCommand)


# ── Chart type normalisation ──────────────────────────────────────────────────

def _normalize_chart_type(chart_type: str) -> Optional[str]:
    """Map chart type variants to their canonical name using AppConfig."""
    if not chart_type:
        return None
    chart_type_lower = chart_type.lower().strip()
    for canonical, variants in AppConfig.CHART_TYPE_VARIANTS.items():
        if chart_type_lower in variants:
            return canonical
    # Return as-is if not found in known variants
    return chart_type_lower


# ── LangGraph node functions ──────────────────────────────────────────────────

def _classify_intent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node: call the LLM and parse output into ParsedCommand."""
    message = state["message"]

    prompt = ChatPromptTemplate.from_template(
        INTENT_PROMPT,
        partial_variables={
            "format_instructions": intent_parser.get_format_instructions()
        },
    )
    chain = prompt | llm | intent_parser

    try:
        result: ParsedCommand = chain.invoke({"message": message})
        logger.debug(f"LLM classified intent: {result.intent} params: {result.params}")
        state["parsed_command"] = result
    except Exception as llm_err:
        logger.warning(
            f"LLM intent classification failed ({llm_err}), "
            "falling back to keyword matching"
        )
        state["parsed_command"] = _fallback_classification(message)

    return state


def _validate_and_normalize_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node: validate intent and normalise chart type params."""
    command: ParsedCommand = state["parsed_command"]

    # Normalise any chart type fields so downstream code uses canonical names
    normalised_params = dict(command.params)
    for field in ("source_type", "target_type", "chart_type"):
        if field in normalised_params:
            normalised_params[field] = _normalize_chart_type(
                str(normalised_params[field])
            )

    # Replace command with a new instance containing normalised params
    state["command"] = ParsedCommand(intent=command.intent, params=normalised_params)
    return state


# ── LangGraph workflow ────────────────────────────────────────────────────────

def _create_intent_graph():
    """Build and compile the LangGraph workflow for intent classification."""
    workflow: StateGraph = StateGraph(Dict[str, Any])
    workflow.add_node("classify", _classify_intent_node)
    workflow.add_node("validate", _validate_and_normalize_node)
    workflow.set_entry_point("classify")
    workflow.add_edge("classify", "validate")
    workflow.add_edge("validate", END)
    return workflow.compile()


# Compiled graph — instantiated once at module import
_intent_graph = _create_intent_graph()


# ── Fallback classification ───────────────────────────────────────────────────

def _fallback_classification(message: str) -> ParsedCommand:
    """
    Keyword-based intent classification used when the LLM call fails.

    Returns a proper ParsedCommand instance — not a raw dict — so that the
    caller never has to handle type differences.
    """
    text = message.lower()

    if any(kw in text for kw in AppConfig.REPLACE_KEYWORDS):
        return ParsedCommand(
            intent=IntentType.REPLACE,
            params=_extract_replace_params(text),
        )

    if any(kw in text for kw in AppConfig.ANALYSIS_KEYWORDS):
        return ParsedCommand(
            intent=IntentType.ANALYSIS,
            params=_extract_analysis_params(text),
        )

    if any(kw in text for kw in AppConfig.DATA_QUERY_KEYWORDS):
        return ParsedCommand(intent=IntentType.DATA_QUERY, params={})

    return ParsedCommand(intent=IntentType.DIRECT, params={})


def _extract_replace_params(text: str) -> Dict[str, Any]:
    """Extract source_type and target_type from a replacement command."""
    params: Dict[str, Any] = {}
    words = text.split()

    try:
        replace_idx = next(
            i for i, w in enumerate(words) if w in ["replace", "swap", "change"]
        )
        with_idx = next(
            (
                i + replace_idx
                for i, w in enumerate(words[replace_idx:])
                if w == "with"
            ),
            None,
        )

        if with_idx is not None:
            source_part = " ".join(words[replace_idx + 1 : with_idx])
            target_part = " ".join(words[with_idx + 1 :])

            for chart_type in AppConfig.CHART_TYPE_VARIANTS:
                if chart_type in source_part:
                    params["source_type"] = chart_type
                if chart_type in target_part:
                    params["target_type"] = chart_type
    except (StopIteration, IndexError):
        pass

    return params


def _extract_analysis_params(text: str) -> Dict[str, Any]:
    """Extract chart_type from an analysis command."""
    for chart_type in AppConfig.CHART_TYPE_VARIANTS:
        if chart_type in text:
            return {"chart_type": chart_type}
    return {}


# ── Public API ────────────────────────────────────────────────────────────────

@trace_function(name="classify_intent", tags=["intent", "classification", "langgraph"])
def classify_intent(message: str) -> IntentType:
    """Classify the intent of a user message. Returns the IntentType enum value."""
    try:
        result = _intent_graph.invoke({"message": message})
        command: ParsedCommand = result["command"]
        return command.intent
    except Exception as err:
        logger.warning(f"Intent graph failed ({err}), using fallback")
        return _fallback_classification(message).intent


@trace_function(name="parse_command", tags=["intent", "parsing", "langgraph"])
def parse_command(message: str) -> ParsedCommand:
    """
    Parse a user message into a structured ParsedCommand.

    Returns a ParsedCommand Pydantic model. Callers use .intent and .params
    directly; there is no to_dict() method — use .model_dump() if a dict is needed.
    """
    try:
        result = _intent_graph.invoke({"message": message})
        return result["command"]
    except Exception as err:
        logger.warning(f"Intent graph failed ({err}), using fallback")
        return _fallback_classification(message)
