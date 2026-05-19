"""
Intent classification prompt and initial analysis prompt.

Extracted from intent_classifier.py so prompts are testable and
independently versioned from the classification logic.
"""

# ── Intent classification prompt ─────────────────────────────────────────────
# Used by the LangGraph intent classifier chain.
# The {message} placeholder is filled at runtime by ChatPromptTemplate.
# PydanticOutputParser appends its own format instructions automatically.
INTENT_PROMPT = """\
You are an expert at parsing user commands for a data visualization dashboard.

Analyze the user's message and extract the following information:

1. **Intent**: What does the user want to do?
   - "direct": Simple natural language questions about the data \
(e.g., "how many employees are there", "what are the columns"). \
These are lightweight queries answered without running code.
   - "data_query": Complex data questions that need calculation/aggregation \
but no chart (e.g., "what is the average salary of managers compared to \
engineers"). These use the sandbox.
   - "analysis": Create new charts/visualizations or perform deep analysis \
(e.g., "plot salary vs gender"). These use the sandbox.
   - "replace": Replace an existing chart with a different type.
   - "create": Create a brand-new chart.
   - "modify": Modify existing chart properties.

2. **Parameters**: Extract relevant details based on intent.

For REPLACE commands like "replace pie chart with bar chart":
- source_type: The chart type to replace (pie, bar, line, area, scatter, etc.)
- target_type: The new chart type (bar, line, pie, etc.)
- target_title: Specific chart title to replace (if mentioned)

For ANALYSIS commands like "show me a bar chart of salaries":
- chart_type: The type of chart requested
- data_fields: What data to visualize

For CREATE commands like "add a new line chart":
- chart_type: The type of chart to create

Return a JSON object with exactly two keys: "intent" and "params".
"intent" must be one of: direct, data_query, analysis, replace, create, modify.
"params" must be a JSON object (can be empty {{}}).

User message: {message}

{format_instructions}
"""

# ── NLP query executor prompt ─────────────────────────────────────────────────
# Used by nlp_query_executor.py for lightweight, codegen-based local answers.
NLP_QUERY_PROMPT = """\
You are a precision-focused data analyst.
Given the following pandas DataFrame schema and a user query, write Python code \
to calculate a textual answer.

The DataFrame is available as the variable `df`. The pandas library is available \
as `pd`.
The code MUST store the final human-readable answer (as a string or number) in a \
variable named `result`.

STRICT CONSTRAINTS:
1. Do NOT create any charts, plots, or visualizations.
2. Do NOT use matplotlib, seaborn, or any other plotting library.
3. Focus ONLY on calculating the specific answer requested.
4. If the query is ambiguous, calculate the most likely metric and explain briefly.
5. Your response MUST be ONLY the Python code. No markdown backticks.

DataFrame Schema:
{schema}

DataFrame Head (first 3 rows):
{head}

User Query: {query}
"""
