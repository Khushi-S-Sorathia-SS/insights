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

# Global variables removed for thread safety in async environment
import json
import re
import math
@trace_function(name="generate_analysis_code", tags=["agent", "code_generation", "deepagents"])
def generate_analysis_code(user_query: str, dataset: DatasetMetadata, raw_data: bytes, chart_rules: str = "", current_widgets_summary: list = None, current_widgets_full: list = None) -> dict:
    """Generate Python code using Deep Agents with Azure OpenAI and Daytona sandbox. Returns dict with output and chart schemas."""

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

        # Upload the full, heavy raw schemas as a file to prevent prompt token overload
        if current_widgets_full:
            sandbox.fs.upload_file(json.dumps(current_widgets_full, indent=2).encode('utf-8'), "/home/daytona/dashboard_schemas.json")

        # Upload the Python helper script for easy schema parsing
        try:
            with open("backend/utils/dashboard_helpers.py", "rb") as f:
                sandbox.fs.upload_file(f.read(), "/home/daytona/dashboard_helpers.py")
        except FileNotFoundError:
            print("Warning: dashboard_helpers.py not found locally. Skipping upload.")

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
- **MANDATORY FOR EVERY CHART OPERATION (INCLUDING REPLACEMENT)**: You MUST write your chart schema(s) as a JSON list to `/home/daytona/chart_schemas.json` using a tool call. This is non-negotiable whether you are creating a new chart or replacing an existing one.
- IMPORTANT: The `/home/daytona/chart_schemas.json` file must contain ONLY raw, valid JSON. Do not wrap it in markdown backticks.
- IMPORTANT: DO NOT mention the file paths or where the charts are saved in your final textual response to the user.
- IMPORTANT: DO NOT output any of your Python code, Pandas DataFrames, or raw data in your final response. Your final response MUST contain ONLY natural language insights.

REPLACEMENT AND AMBIGUITY RULES:
- If the user asks to "replace", "change", "swap", or "use [X] instead of [Y]", follow these steps:
  1. Identify the target chart ID from the dashboard summary below.
  2. Use Python code to load the source data FROM the existing chart schema or from `data.csv` if needed.
  3. Build a new chart schema JSON object with the same data but the new chart type.
  4. Add a `"replace_id": "THE_MATCHING_WIDGET_ID"` field to that JSON object.
  5. Write the JSON object (in a list) to `/home/daytona/chart_schemas.json` using a write_file tool call.
- A lightweight summary of the current dashboard components is:
  {current_widgets_summary if current_widgets_summary else "[]"}
- If you need to inspect the full schemas (e.g. to get the exact data from an existing chart), load `/home/daytona/dashboard_schemas.json` using the dashboard helper:
  ```python
  from dashboard_helpers import helper
  bar_charts = helper.find_widgets_by_type("bar")
  donut_charts = helper.find_widgets_by_title("donut")
  # Each result has: id, component_type, schema (which contains type, title, data, xAxis, yAxis)
  ```
- **FALLBACK**: If you find multiple matching charts and are not confident which one to replace, output a textual response asking the user: e.g. "I found 'Revenue Distribution' and 'Department Distribution'. Which should I replace?" and do NOT write any chart schemas.
- If you are adding a new chart that doesn't replace anything, do not include "replace_id".
- **LAYOUT SIZING**: For every chart you write to `/home/daytona/chart_schemas.json`, include:
    - `"w"`: Width on a 12-column grid. (e.g., 4 for small, 6 for medium, 12 for full-width).
    - `"h"`: Height in grid units (e.g., 3 for simple cards, 5 for complex charts).
- IMPORTANT: You MUST output valid JSON. No markdown.

FINAL RESPONSE RULES:
- Your final answer MUST be ONLY natural language insights.
- NEVER include python code, markdown code blocks, file paths (like /home/daytona/...), or technical debugging info in your final response.
- If you generated or replaced charts, summarize what the chart shows in 1-2 sentences.

CHART SCHEMA RULES:
{chart_rules if chart_rules else "No specific rules provided. Use generic representations."}

- Be precise and efficient in your code generation

You have access to filesystem tools (read_file, write_file, edit_file, ls, glob, grep) and can execute shell commands in the sandbox.
IMPORTANT: You MUST use your tools. Do NOT simply describe what you would do. For any chart output, write a file using write_file. For any code, write it to a file and run it with your shell tool."""

        # Create the Deep Agent
        agent = create_deep_agent(
            model=llm,
            system_prompt=system_prompt,
            backend=backend,
        )

        # Prepare the user message — must be forceful about tool use
        user_message = f"""User Query: {user_query}

IMPORTANT: You MUST use your tools to complete this task. Do NOT just describe what you would do.
- If this is a replacement/chart change: read the existing chart schema from dashboard_schemas.json, build the new schema JSON, and write it to /home/daytona/chart_schemas.json using write_file.
- If this is a new chart request: write Python code to analyze data.csv, compute the chart data, and write the chart schema to /home/daytona/chart_schemas.json.
- Then provide a short natural language summary in your final response."""

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
            output_text = re.sub(r'```.*?```', '', content, flags=re.DOTALL).strip()
            # Also strip any stray single backticks or common path patterns
            output_text = re.sub(r'/home/daytona/\S+', '', output_text).strip()
            
            # If the LLM ONLY output code and no text, don't leave it completely empty
            if not output_text and content.strip():
                output_text = "Analysis code executed successfully, but no natural language summary was provided."
        else:
            output_text = "Analysis completed."

        # Retrieve chart schemas from the ephemeral Daytona sandbox
        try:
            # Use the Daytona sandbox filesystem API directly to read the generated schemas.
            # The Daytona sandbox is a remote environment, and this is the most reliable way to pull files.
            print(f"DEBUG: Attempting to download chart_schemas.json from sandbox...")
            try:
                output_bytes = sandbox.fs.download_file("/home/daytona/chart_schemas.json")
                output_str = output_bytes.decode("utf-8").strip()
                print(f"DEBUG: Downloaded {len(output_str)} chars from sandbox.")
            except Exception as e:
                print(f"DEBUG: Chart schema file not found or unreadable in sandbox: {e}")
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
                        
                print(f"DEBUG: Parsing Chart Schemas: {output_str[:200]}...")
                last_execution_charts = json.loads(output_str)
                print(f"DEBUG: Successfully parsed {len(last_execution_charts)} charts from file.")
                
                # Clean NaN and Infinity values from chart schemas to make them JSONB-compatible
                def clean_numeric_values(obj):
                    if isinstance(obj, dict):
                        return {k: clean_numeric_values(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [clean_numeric_values(item) for item in obj]
                    elif isinstance(obj, float):
                        if math.isnan(obj) or math.isinf(obj):
                            return None
                        return obj
                    else:
                        return obj
                
                chart_schemas = [clean_numeric_values(chart) for chart in last_execution_charts]
            else:
                print("DEBUG: No chart schemas found in sandbox file. Attempting fallback parse from response text...")
                # Fallback: Try to find JSON in the response text if the file is missing/empty
                # We must use 'content' here because 'output_text' has already been stripped of markdown blocks
                match = re.search(r"\[\s*\{.*\}\s*\]", content, re.DOTALL)
                if match:
                    try:
                        potential_json = match.group(0)
                        chart_schemas = json.loads(potential_json)
                        print(f"DEBUG: Fallback parsed {len(chart_schemas)} charts from response text.")
                    except:
                        chart_schemas = []
                else:
                    chart_schemas = []
        except Exception as e:
            # If chart retrieval or parsing fails, continue without schemas
            print(f"DEBUG: Failed to parse charts: {e}")
            chart_schemas = []

        # Return both output text and captured chart schemas
        return {
            "output": output_text,
            "chart_schemas": chart_schemas
        }

    finally:
        # Clean up the sandbox
        try:
            sandbox.delete()
        except Exception:
            pass  # Ignore cleanup errors
