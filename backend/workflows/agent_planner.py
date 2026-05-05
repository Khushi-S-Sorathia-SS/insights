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
register_harness_profile(
    "openai",
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
def generate_analysis_code(user_query: str, dataset: DatasetMetadata) -> dict:
    """Generate Python code using Deep Agents with Azure OpenAI and Daytona sandbox. Returns dict with output and charts."""
    global current_dataset_path, last_execution_charts
    current_dataset_path = dataset.file_path
    last_execution_charts = []  # Reset for new execution

    # Initialize Daytona client for this session
    daytona_client = Daytona()
    
    # Create a sandbox for this session
    sandbox = daytona_client.create()
    backend = DaytonaSandbox(sandbox=sandbox)

    try:
        # Upload the dataset file to the sandbox
        dataset_filename = Path(dataset.file_path).name
        sandbox_dataset_path = f"/tmp/{dataset_filename}"
        with open(dataset.file_path, 'rb') as f:
            dataset_content = f.read()

        backend.upload_files([
            (sandbox_dataset_path, dataset_content)
        ])

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
2. Generate complete, executable Python code that loads the dataset and performs the analysis
3. Execute your generated code using the available tools
4. Analyze the results and provide insights

CRITICAL REQUIREMENTS:
- The dataset is available at {sandbox_dataset_path}
- Always inspect the dataset structure first before making assumptions about columns
- Generate code that SAVES charts as PNG files in /tmp/ (e.g., plt.savefig('/tmp/chart_name.png', dpi=100, bbox_inches='tight'))
- For initial dataset overview: Create at least 2-3 visualizations:
  * Distribution plots for numeric columns
  * Count plots for categorical columns
  * Correlation heatmap if there are numeric columns
- Use plt.figure(figsize=(10, 6)) for better chart sizes
- Close plots after saving: plt.close()
- Be precise and efficient in your code generation
- IMPORTANT: Save all charts before running any analysis code

You have access to filesystem tools (read_file, write_file, edit_file, ls, glob, grep) and can execute shell commands in the sandbox."""

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

        # Extract the final answer
        output_text = ""
        if result and "messages" in result:
            # Get the last message from the agent
            last_message = result["messages"][-1]
            if hasattr(last_message, 'content'):
                output_text = last_message.content
            else:
                output_text = str(last_message)
        else:
            output_text = "Analysis completed. Check the results above."

        # Retrieve any generated charts from the sandbox
        try:
            # List PNG files in the temp directory
            chart_files = []
            ls_result = backend.execute("ls /tmp/*.png")
            if ls_result.output.strip():
                chart_files = [line.strip() for line in ls_result.output.strip().split('\n') if line.strip()]

            charts = []
            if chart_files:
                # Download the chart files
                download_results = backend.download_files([f"/tmp/{Path(f).name}" for f in chart_files])
                for download_result in download_results:
                    if download_result.content:
                        charts.append(base64.b64encode(download_result.content).decode("utf-8"))

            last_execution_charts = charts
        except Exception as e:
            # If chart retrieval fails, continue without charts
            last_execution_charts = []

        # Return both output text and captured charts
        return {
            "output": output_text,
            "charts": last_execution_charts
        }

    finally:
        # Clean up the sandbox
        try:
            sandbox.stop()
        except Exception:
            pass  # Ignore cleanup errors
