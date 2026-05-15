import pandas as pd
import re
from typing import Any
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from ..config import Settings
from ..utils.logger import get_logger

logger = get_logger(__name__)

settings = Settings()
llm = AzureChatOpenAI(
    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
    azure_deployment=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
    api_version=settings.AZURE_OPENAI_API_VERSION,
    api_key=settings.AZURE_OPENAI_API_KEY,
    temperature=0,
)

PROMPT_TEMPLATE = """
You are a precision-focused data analyst.
Given the following pandas DataFrame schema and a user query, write Python code to calculate a textual answer.

The DataFrame is available as the variable `df`. The pandas library is available as `pd`.
The code MUST store the final human-readable answer (as a string or number) in a variable named `result`.

STRICT CONSTRAINTS:
1. Do NOT create any charts, plots, or visualizations.
2. Do NOT use matplotlib, seaborn, or any other plotting library.
3. Focus ONLY on calculating the specific answer requested.
4. If the query is ambiguous, calculate the most likely metric and explain it briefly.
5. Your response MUST be ONLY the Python code. No markdown backticks.

DataFrame Schema:
{schema}

DataFrame Head (first 3 rows):
{head}

User Query: {query}
"""

def execute_nlp_query(query: str, df: pd.DataFrame) -> str:
    """Executes a natural language query against a pandas DataFrame using lightweight local execution."""
    try:
        # Get schema and head for context
        schema = str(df.dtypes)
        head = df.head(3).to_string()
        
        prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
        chain = prompt | llm
        
        response = chain.invoke({"schema": schema, "head": head, "query": query})
        code = response.content.strip()
        
        # Clean up any potential markdown formatting
        code = re.sub(r'```python\n|```\n|```', '', code)
        
        logger.info(f"Executing lightweight NLP code:\n{code}")
        
        # Execute the code in a restricted dictionary
        local_env = {"pd": pd, "df": df}
        # Note: We use exec here for "lightweight" execution as requested, 
        # but in a production environment with untrusted users, 
        # a more restricted sandbox would still be preferred.
        exec(code, {"__builtins__": {}}, local_env)
        
        if "result" in local_env:
            res = local_env["result"]
            if isinstance(res, (int, float)):
                return f"The result is {res}"
            return str(res)
        else:
            return "I analyzed the data but couldn't format a final answer. Could you rephrase your question?"
            
    except Exception as e:
        logger.error(f"Error executing NLP query: {e}")
        return f"I encountered an error trying to answer your question: {str(e)}"
