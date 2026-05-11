"""
Agent planner using Deep Agents with Azure OpenAI for generating Python analysis code.
Integrated with LangSmith for execution tracing and Daytona sandbox for secure execution.
"""

import base64
from pathlib import Path
from typing import Dict

from langchain_openai import AzureChatOpenAI
from deepagents import create_deep_agent, HarnessProfileConfig, register_harness_profile
from langchain_daytona import DaytonaSandbox
from daytona import Daytona

from ..models.session import DatasetMetadata
from ..utils.langsmith_tracer import trace_function
from ..config import get_settings

settings = get_settings()

# DeepAgents is used only with Azure OpenAI in this app.
# Exclude Anthropic-specific prompt-caching middleware to avoid unrelated provider labels in traces.
# Register profiles for both 'openai' (generic) and 'azure' (specific for AzureChatOpenAI)
# to ensure Anthropic-specific middleware is excluded and doesn't interfere with the response.
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
    temperature=0.1,
)

# Global variables for current dataset path and execution results
current_dataset_path = None
last_execution_charts = []


@trace_function(name="generate_analysis_code", tags=["agent", "code_generation", "deepagents"])
def generate_analysis_code(user_query: str, dataset: DatasetMetadata, raw_data: bytes, chart_rules: str = "", current_widgets: list = None) -> dict:
    """Generate Python code using Deep Agents with Azure OpenAI and Daytona sandbox. Returns dict with output and chart schemas."""
    global current_dataset_path, last_execution_charts
    current_dataset_path = None  # No local file path; data comes from PostgreSQL
    last_execution_charts = []  # Reset for new execution

    # Initialize Daytona client for this session
    daytona_client = Daytona()
    
    # Create a sandbox for this session
    sandbox = daytona_client.create()
    backend = DaytonaSandbox(sandbox=sandbox)

    try:
        # Upload raw CSV bytes directly into the sandbox.
        # The Daytona sandbox is a remote cloud environment that CANNOT access
        # the local Docker network (postgres:5432 / host.docker.internal are unreachable).
        # Data is already saved in PostgreSQL by file_manager. Here we just give
        # the agent a local copy to work with.
        # Standardize path to 'data.csv' to avoid issues with spaces or special chars in filename
        sandbox_path = "/home/daytona/data.csv"
        sandbox.fs.upload_file(raw_data, sandbox_path)

        # Create the system prompt
        system_prompt = f"""You are an expert data analyst. Given a user query and dataset information, generate and execute Python code to analyze the data and answer the query.

Dataset information:
- Filename: {dataset.filename}
- Columns: {", ".join(dataset.columns)}
- Data Types: {", ".join([f"{col}: {dtype}" for col, dtype in dataset.dtypes.items()])}
- Sample Rows:
{chr(10).join([str(row) for row in dataset.preview_rows[:3]])}

Your job is to:
1. Understand the user's query and dataset structure
2. **VALIDATE COLUMNS FIRST**: Before doing anything else, check if ALL columns mentioned in the user query actually exist in the dataset. The EXACT available columns are: {", ".join(dataset.columns)}
3. If the user's query references a column that does NOT exist (e.g., "Job Category" when it is not in the dataset), you MUST:
   - Immediately stop and do NOT generate a chart.
   - Respond clearly: "The column '[column_name]' does not exist in this dataset. The available columns are: {', '.join(dataset.columns)}."
   - Do NOT write any chart schemas.
4. Only if all required columns exist: Generate complete, executable Python code that loads the dataset and performs the analysis
5. Execute your generated code using the available tools
6. Analyze the results and provide insights

MANDATORY FIRST CODE STEP:
Your very FIRST code execution MUST always be:
```python
import subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pandas"])

import pandas as pd

df = pd.read_csv("{sandbox_path}")
print("Columns:", df.columns.tolist())
print("Dtypes:", df.dtypes.to_dict())
print("Shape:", df.shape)
print(df.head(3))
```
Use the EXACT column names from this output. Do NOT rename or guess column names.

CRITICAL REQUIREMENTS:
- The dataset is available as a local CSV file at `{sandbox_path}`. Read it with pd.read_csv().
- Do NOT try to connect to any database. The file is already in the sandbox.
- NEVER invent, guess, or substitute column names. If a column is missing, say so explicitly.
- When grouping by a string/categorical column (like job categories, departments, gender), the grouped column values ARE STRINGS. Never try to convert them to int or float. Use them as-is for labels.
- For chart data objects, category/label fields must be strings, and value fields must be numbers. Example: {{"jobcat": "Manager", "count": 84}} — "Manager" stays a string, count is a number.
- DO NOT generate matplotlib charts or save PNG files. Instead, compute the necessary metrics/aggregations and output STRICTLY formatted JSON matching the required chart schema.
- Save all generated chart schema JSON objects as a JSON list into a file at `/home/daytona/chart_schemas.json` (inside the sandbox).
- IMPORTANT: The `/home/daytona/chart_schemas.json` file must contain ONLY raw, valid JSON. Do not wrap it in markdown backticks.
- IMPORTANT: DO NOT mention the file paths or where the charts are saved in your final textual response to the user.
- IMPORTANT: DO NOT output any of your Python code, Pandas DataFrames, or raw data in your final response. Your final response MUST contain ONLY natural language insights.

REPLACEMENT AND AMBIGUITY RULES:
- If the user asks to "replace", "change", "swap", or "use [X] instead of [Y]", you MUST identify the ID of the chart to be replaced from the following list:
  {current_widgets if current_widgets else "[]"}
- Look at the "title" and "type" in the list above to find the match.
- If you find a match, your output in `/home/daytona/chart_schemas.json` MUST include a `"replace_id": "THE_MATCHING_WIDGET_ID"` field inside the chart object.
- If there is ambiguity (multiple charts with same type/title), STOP and ask the user for clarification.
- If you are adding a new chart that doesn't replace anything, do not include "replace_id".
- IMPORTANT: You MUST output valid JSON. No markdown.

FINAL RESPONSE RULES:
- Your final answer MUST be ONLY natural language insights.
- NEVER include python code, markdown code blocks, file paths (like /home/daytona/...), or technical debugging info in your final response.
- If you generated charts, summarize what they show in 1-2 sentences.

CHART SCHEMA RULES:
{chart_rules if chart_rules else "No specific rules provided. Use generic representations."}

- Be precise and efficient in your code generation

You have access to filesystem tools (read_file, write_file, edit_file, ls, glob, grep) and can execute shell commands in the sandbox.
IMPORTANT: To execute Python code, you must use a tool. Do NOT simply output the code in your response. Write your Python code to a file (e.g., /home/daytona/analyze.py) and then execute it using the shell tool with `python3 /home/daytona/analyze.py`."""

        # Create the Deep Agent
        agent = create_deep_agent(
            model=llm,
            system_prompt=system_prompt,
            backend=backend,
        )

        # Prepare the user message
        user_message = f"""User Query: {user_query}

Please analyze the dataset and answer the query. Generate and execute Python code as needed."""

        # Invoke the agent
        result = agent.invoke({
            "messages": [
                {
                    "role": "user",
                    "content": user_message,
                }
            ]
        })

        # Extract the final answer and strip any code blocks
        output_text = ""
        if result and "messages" in result:
            last_message = result["messages"][-1]
            content = last_message.content if hasattr(last_message, 'content') else str(last_message)
            
            # Use regex to strip ANY markdown code blocks (python, json, etc)
            import re
            output_text = re.sub(r'```.*?```', '', content, flags=re.DOTALL).strip()
            # Also strip any stray single backticks or common path patterns
            output_text = re.sub(r'/home/daytona/\S+', '', output_text)
        else:
            output_text = "Analysis completed."

        # Retrieve chart schemas from the ephemeral Daytona sandbox
        import json
        import re
        import math
        try:
            # Use the Daytona sandbox filesystem API directly to read the generated schemas.
            # The Daytona sandbox is a remote environment, and this is the most reliable way to pull files.
            try:
                output_bytes = sandbox.fs.download_file("/home/daytona/chart_schemas.json")
                output_str = output_bytes.decode("utf-8").strip()
            except Exception as e:
                print(f"Chart schema file not found or unreadable: {e}")
                output_str = ""
            
            if output_str:
                # Clean up any potential markdown formatting from the LLM (if it wrote backticks into the file)
                if "```json" in output_str:
                    match = re.search(r"```json\s*(.*?)\s*```", output_str, re.DOTALL)
                    if match:
                        output_str = match.group(1)
                elif "```" in output_str:
                    match = re.search(r"```\s*(.*?)\s*```", output_str, re.DOTALL)
                    if match:
                        output_str = match.group(1)
                        
                print(f"DEBUG CHART SCHEMAS: {output_str}")
                last_execution_charts = json.loads(output_str)
                
                # Clean NaN values from chart schemas to make them JSONB-compatible
                def clean_nan(obj):
                    if isinstance(obj, dict):
                        return {k: clean_nan(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [clean_nan(item) for item in obj]
                    elif isinstance(obj, float) and math.isnan(obj):
                        return None
                    else:
                        return obj
                
                last_execution_charts = [clean_nan(chart) for chart in last_execution_charts]
            else:
                last_execution_charts = []
        except Exception as e:
            # If chart retrieval or parsing fails, continue without schemas
            print(f"Failed to parse charts: {e}")
            last_execution_charts = []

        # Return both output text and captured chart schemas
        return {
            "output": output_text,
            "chart_schemas": last_execution_charts
        }

    finally:
        # Clean up the sandbox
        try:
            sandbox.delete()
        except Exception:
            pass  # Ignore cleanup errors
