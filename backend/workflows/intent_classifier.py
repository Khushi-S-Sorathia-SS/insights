"""
Intent classification for user queries.
Integrated with LangSmith for execution tracing.
"""

from enum import Enum
from ..utils.langsmith_tracer import trace_function


class IntentType(str, Enum):
    DIRECT = "direct"
    ANALYSIS = "analysis"


ANALYSIS_KEYWORDS = {
    "plot",
    "chart",
    "visual",
    "compare",
    "vs",
    "distribution",
    "trend",
    "breakdown",
    "group",
    "graph",
    "scatter",
    "bar",
    "hist",
    "headcount",
    "average",
    "mean",
    "sum",
}

DIRECT_KEYWORDS = {
    "missing",
    "duplicate",
    "duplicates",
    "summary",
    "insights",
    "count",
    "how many",
    "what is",
    "who",
    "where",
    "when",
}


@trace_function(name="classify_intent", tags=["intent", "classification"])
def classify_intent(message: str) -> IntentType:
    """Classify user message intent as DIRECT or ANALYSIS."""
    text = message.lower()

    if any(keyword in text for keyword in ANALYSIS_KEYWORDS):
        return IntentType.ANALYSIS

    if any(keyword in text for keyword in DIRECT_KEYWORDS):
        return IntentType.DIRECT

    return IntentType.DIRECT
