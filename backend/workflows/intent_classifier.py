"""
Intent classification for user queries using LangGraph.
Integrated with LangSmith for execution tracing.
"""

from enum import Enum
from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langchain_openai import AzureChatOpenAI
from ..config import Settings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from ..utils.langsmith_tracer import trace_function


class IntentType(str, Enum):
    DIRECT = "direct"
    ANALYSIS = "analysis"
    REPLACE = "replace"
    CREATE = "create"
    MODIFY = "modify"


class ParsedCommand:
    def __init__(self, intent: IntentType, params: Dict[str, Any]):
        self.intent = intent
        self.params = params

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent.value,
            "params": self.params
        }


# Initialize Azure OpenAI LLM
settings = Settings()
llm = AzureChatOpenAI(
    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
    azure_deployment=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
    api_version=settings.AZURE_OPENAI_API_VERSION,
    api_key=settings.AZURE_OPENAI_API_KEY,
    temperature=0,
)

# Define the prompt for intent classification
INTENT_PROMPT = """
You are an expert at parsing user commands for a data visualization dashboard.

Analyze the user's message and extract the following information:

1. **Intent**: What does the user want to do?
   - "direct": Simple questions about data (counts, summaries, missing values)
   - "analysis": Create new charts/visualizations
   - "replace": Replace an existing chart with a different type
   - "create": Create a new chart
   - "modify": Modify existing chart properties

2. **Parameters**: Extract relevant details based on intent

For REPLACE commands like "replace pie chart with bar chart":
- source_type: The chart type to replace (pie, bar, line, area, scatter, etc.)
- target_type: The new chart type (bar, line, pie, etc.)
- target_title: Specific chart title to replace (if mentioned)

For ANALYSIS commands like "show me a bar chart of salaries":
- chart_type: The type of chart requested
- data_fields: What data to visualize

For CREATE commands like "add a new line chart":
- chart_type: The type of chart to create

Return the result as a JSON object with "intent" and "params" keys.

User message: {message}

Return only valid JSON.
"""

intent_parser = JsonOutputParser()


def create_intent_graph():
    """Create the LangGraph workflow for intent classification."""

    def classify_intent_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Node to classify intent using LLM."""
        message = state["message"]

        prompt = ChatPromptTemplate.from_template(INTENT_PROMPT)
        chain = prompt | llm | intent_parser

        try:
            result = chain.invoke({"message": message})
            state["parsed"] = result
        except Exception as e:
            # Fallback to simple keyword matching if LLM fails
            state["parsed"] = fallback_classification(message)

        return state

    def validate_and_normalize_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Node to validate and normalize the parsed result."""
        parsed = state["parsed"]

        # Ensure intent is valid
        intent_str = parsed.get("intent", "direct")
        try:
            intent = IntentType(intent_str)
        except ValueError:
            intent = IntentType.DIRECT

        # Normalize parameters
        params = parsed.get("params", {})

        # Normalize chart types
        chart_types = {
            "pie": ["pie", "piechart", "pie chart"],
            "bar": ["bar", "barchart", "bar chart", "column"],
            "line": ["line", "linechart", "line chart"],
            "area": ["area", "areachart", "area chart"],
            "scatter": ["scatter", "scatterplot", "scatter plot"],
            "radar": ["radar", "radar chart"],
            "histogram": ["hist", "histogram", "distribution"],
        }

        def normalize_chart_type(chart_type: str) -> Optional[str]:
            if not chart_type:
                return None
            chart_type_lower = chart_type.lower()
            for normalized, variants in chart_types.items():
                if chart_type_lower in variants:
                    return normalized
            return chart_type_lower

        if "source_type" in params:
            params["source_type"] = normalize_chart_type(params["source_type"])
        if "target_type" in params:
            params["target_type"] = normalize_chart_type(params["target_type"])
        if "chart_type" in params:
            params["chart_type"] = normalize_chart_type(params["chart_type"])

        state["command"] = ParsedCommand(intent, params)
        return state

    # Create the graph
    workflow = StateGraph(Dict[str, Any])

    # Add nodes
    workflow.add_node("classify", classify_intent_node)
    workflow.add_node("validate", validate_and_normalize_node)

    # Add edges
    workflow.set_entry_point("classify")
    workflow.add_edge("classify", "validate")
    workflow.add_edge("validate", END)

    return workflow.compile()


def fallback_classification(message: str) -> Dict[str, Any]:
    """Fallback classification using keyword matching."""
    text = message.lower()

    # Check for replace commands
    replace_keywords = ["replace", "swap", "change", "switch", "instead"]
    if any(keyword in text for keyword in replace_keywords):
        return {
            "intent": "replace",
            "params": extract_replace_params(text)
        }

    # Check for analysis commands
    analysis_keywords = ["plot", "chart", "visual", "graph", "show", "create", "add"]
    if any(keyword in text for keyword in analysis_keywords):
        return {
            "intent": "analysis",
            "params": extract_analysis_params(text)
        }

    # Default to direct
    return {
        "intent": "direct",
        "params": {}
    }


def extract_replace_params(text: str) -> Dict[str, Any]:
    """Extract parameters from replace commands."""
    params = {}

    # Simple extraction - look for "replace X with Y"
    words = text.split()
    try:
        replace_idx = next(i for i, word in enumerate(words) if word in ["replace", "swap", "change"])
        with_idx = next((i for i, word in enumerate(words[replace_idx:]) if word == "with"), None)

        if with_idx is not None:
            with_idx += replace_idx
            source_part = " ".join(words[replace_idx+1:with_idx])
            target_part = " ".join(words[with_idx+1:])

            # Extract chart types
            chart_types = ["pie", "bar", "line", "area", "scatter", "radar", "histogram"]
            for chart_type in chart_types:
                if chart_type in source_part.lower():
                    params["source_type"] = chart_type
                if chart_type in target_part.lower():
                    params["target_type"] = chart_type

    except (StopIteration, IndexError):
        pass

    return params


def extract_analysis_params(text: str) -> Dict[str, Any]:
    """Extract parameters from analysis commands."""
    params = {}

    chart_types = ["pie", "bar", "line", "area", "scatter", "radar", "histogram"]
    for chart_type in chart_types:
        if chart_type in text:
            params["chart_type"] = chart_type
            break

    return params


# Global graph instance
intent_graph = create_intent_graph()


@trace_function(name="classify_intent", tags=["intent", "classification", "langgraph"])
def classify_intent(message: str) -> IntentType:
    """Classify user message intent using LangGraph."""
    try:
        result = intent_graph.invoke({"message": message})
        command = result["command"]
        return command.intent
    except Exception as e:
        # Fallback to simple classification
        fallback = fallback_classification(message)
        return IntentType(fallback["intent"])


@trace_function(name="parse_command", tags=["intent", "parsing", "langgraph"])
def parse_command(message: str) -> ParsedCommand:
    """Parse user message into structured command using LangGraph."""
    try:
        result = intent_graph.invoke({"message": message})
        return result["command"]
    except Exception as e:
        # Fallback parsing
        fallback = fallback_classification(message)
        intent = IntentType(fallback["intent"])
        return ParsedCommand(intent, fallback["params"])
