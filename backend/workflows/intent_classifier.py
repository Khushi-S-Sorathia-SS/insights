"""
Intent classification for user queries.
"""

from enum import Enum


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


def classify_intent(message: str) -> IntentType:
    text = message.lower()

    if any(keyword in text for keyword in ANALYSIS_KEYWORDS):
        return IntentType.ANALYSIS

    if any(keyword in text for keyword in DIRECT_KEYWORDS):
        return IntentType.DIRECT

    return IntentType.DIRECT
