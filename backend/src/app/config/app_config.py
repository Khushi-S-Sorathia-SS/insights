"""
AppConfig — static application constants.

This is NOT a Pydantic model and NOT env-driven.
It holds purely static, hardcoded rules and defaults that do not vary
by environment (security rules, allowed types, structural constraints).

For env-configurable values (temperatures, timeouts, URIs) see settings.py.
"""


class AppConfig:
    """Static application constants grouped by domain."""

    # ── File Upload Validation ────────────────────────────────────────────────
    ALLOWED_FILE_TYPES: frozenset[str] = frozenset({".csv"})
    MAX_UPLOAD_SIZE_MB: int = 10

    # Known column names the system is aware of (used for CSV validation context)
    ALLOWED_CSV_COLUMNS: frozenset[str] = frozenset({
        "name", "id", "employee_id", "department", "salary",
        "experience", "gender", "age", "position", "hire_date",
        "status", "rating", "attendance", "projects",
    })

    # ── Sandbox Code Security ─────────────────────────────────────────────────
    ALLOWED_IMPORTS: frozenset[str] = frozenset({
        "pandas",
        "numpy",
        "matplotlib",
        "io",
        "base64",
        "json",
    })

    FORBIDDEN_IMPORTS: frozenset[str] = frozenset({
        "os",
        "sys",
        "subprocess",
        "requests",
        "urllib",
        "pickle",
        "dill",
        "importlib",
        "__import__",
        "eval",
        "exec",
    })

    # ── Sandbox Execution Defaults ────────────────────────────────────────────
    DEFAULT_SANDBOX_TIMEOUT: int = 20       # seconds
    DEFAULT_SANDBOX_MEMORY_LIMIT: str = "512M"

    # ── Dataset Preview ───────────────────────────────────────────────────────
    # Number of rows shown in dataset preview (used by file_manager)
    PREVIEW_ROWS_COUNT: int = 5

    # ── Dashboard Grid Layout ─────────────────────────────────────────────────
    # Total columns in the 12-column grid system
    GRID_COLUMNS: int = 12
    # Default widget width (half grid width)
    DEFAULT_WIDGET_WIDTH: int = 6
    # Default widget height in grid units
    DEFAULT_WIDGET_HEIGHT: int = 4
    # Smaller height for insight/text widgets
    INSIGHT_WIDGET_HEIGHT: int = 3

    # ── HTTP Response Codes ───────────────────────────────────────────────────
    SUCCESS_RESPONSE_CODE: int = 200
    CREATED_RESPONSE_CODE: int = 201
    BAD_REQUEST_CODE: int = 400
    UNAUTHORIZED_CODE: int = 401
    FORBIDDEN_CODE: int = 403
    NOT_FOUND_CODE: int = 404
    INTERNAL_ERROR_CODE: int = 500

    # ── Chart Types ───────────────────────────────────────────────────────────
    # Canonical chart type names and their accepted variants
    CHART_TYPE_VARIANTS: dict[str, list[str]] = {
        "pie":       ["pie", "piechart", "pie chart"],
        "donut":     ["donut", "donutchart", "donut chart"],
        "bar":       ["bar", "barchart", "bar chart", "column"],
        "line":      ["line", "linechart", "line chart"],
        "area":      ["area", "areachart", "area chart"],
        "scatter":   ["scatter", "scatterplot", "scatter plot"],
        "radar":     ["radar", "radar chart"],
        "histogram": ["hist", "histogram", "distribution"],
    }

    # ── Intent Classification Keywords ───────────────────────────────────────
    REPLACE_KEYWORDS: list[str] = ["replace", "swap", "change", "switch", "instead"]
    ANALYSIS_KEYWORDS: list[str] = ["plot", "chart", "visual", "graph", "show", "create", "add"]
    DATA_QUERY_KEYWORDS: list[str] = [
        "how many", "count", "average", "mean", "median",
        "sum", "total", "percentage", "proportion", "what is", "calculate",
    ]
