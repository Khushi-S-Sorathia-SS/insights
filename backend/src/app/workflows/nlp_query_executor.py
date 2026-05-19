"""
Lightweight NLP query executor for direct/simple data questions.

Uses LLM_TEMPERATURE_NLP (deterministic: 0.0) to generate executable Python code
that runs locally against a pandas DataFrame — no Daytona sandbox needed.
Used only for IntentType.DIRECT queries where no charts are produced.
"""

import re

import pandas as pd
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI

from src.app.config.settings import get_settings
from src.app.prompts.intent_classification import NLP_QUERY_PROMPT
from src.app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

# ── LLM initialisation ────────────────────────────────────────────────────────
# Separate instance from agent_planner — deterministic (temp=0), lightweight queries
llm = AzureChatOpenAI(
    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
    azure_deployment=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
    api_version=settings.AZURE_OPENAI_API_VERSION,
    api_key=settings.AZURE_OPENAI_API_KEY,
    temperature=settings.LLM_TEMPERATURE_NLP,
)


def execute_nlp_query(query: str, df: pd.DataFrame) -> str:
    """
    Answer a user query by generating and executing lightweight Python code locally.

    The LLM writes code that operates on `df` (already loaded in memory) and stores
    the final answer in a variable named `result`. We execute it in a restricted
    local namespace and return the result as a string.

    This is safe for DIRECT intent queries only — the data is already trusted
    (it came from the DB) and no file I/O or subprocess is allowed.

    Parameters
    ----------
    query:
        The user's natural language question.
    df:
        The dataset as a pandas DataFrame.

    Returns
    -------
    str
        A human-readable answer derived from the data.
    """
    try:
        schema = str(df.dtypes)
        head = df.head(3).to_string()

        prompt = ChatPromptTemplate.from_template(NLP_QUERY_PROMPT)
        chain = prompt | llm

        response = chain.invoke({"schema": schema, "head": head, "query": query})
        code = response.content.strip()

        # Strip accidental markdown fences from the LLM response
        code = re.sub(r"```python\n|```\n|```", "", code).strip()

        logger.info(f"Executing lightweight NLP code for query: {query[:60]!r}")
        logger.debug(f"Generated code:\n{code}")

        # Execute in a tightly restricted namespace
        # __builtins__ is set to empty dict to prevent access to built-in functions
        # that could be misused (import, open, eval, exec, etc.)
        local_env: dict = {"pd": pd, "df": df}
        exec(code, {"__builtins__": {}}, local_env)  # noqa: S102

        if "result" in local_env:
            res = local_env["result"]
            if isinstance(res, (int, float)):
                return f"The result is {res}"
            return str(res)

        return (
            "I analyzed the data but could not format a final answer. "
            "Could you rephrase your question?"
        )

    except Exception as err:
        logger.error(f"NLP query execution failed for query {query[:60]!r}: {err}")
        return f"I encountered an error trying to answer your question: {err}"
