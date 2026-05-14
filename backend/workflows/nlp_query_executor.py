import pandas as pd
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
You are an expert Python data analyst.
Given the following pandas DataFrame schema and a user query, write Python code to calculate the answer.
The DataFrame is available as the variable `df`. The pandas library is available as `pd`.
The code MUST store the final human-readable answer (as a string) in a variable named `result`.
Do not create any charts or visualizations.
Ensure your code is safe and does not perform any destructive operations.

DataFrame Schema:
{schema}

DataFrame Head (first 3 rows):
{head}

User Query: {query}

Return ONLY the Python code. Do not include markdown formatting (like ```python) or any other text.
"""

def execute_nlp_query(query: str, df: pd.DataFrame) -> str:
    """Executes a natural language query against a pandas DataFrame using LLM code generation."""
    try:
        # Get schema and head for context
        schema = str(df.dtypes)
        head = df.head(3).to_string()
        
        prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
        chain = prompt | llm
        
        response = chain.invoke({"schema": schema, "head": head, "query": query})
        code = response.content.strip()
        
        # Clean up markdown if LLM still included it
        if code.startswith("```python"):
            code = code[9:]
        elif code.startswith("```"):
            code = code[3:]
        if code.endswith("```"):
            code = code[:-3]
        code = code.strip()
        
        logger.info(f"Generated NLP query code:\n{code}")
        
        # Execute the code in a restricted dictionary
        local_env = {"pd": pd, "df": df}
        exec(code, {}, local_env)
        
        if "result" in local_env:
            return str(local_env["result"])
        else:
            return "Analysis complete, but the 'result' variable was not found in the generated code."
            
    except Exception as e:
        logger.error(f"Error executing NLP query: {e}")
        return f"I encountered an error trying to answer your question: {str(e)}"
