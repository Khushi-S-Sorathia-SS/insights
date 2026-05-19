"""
Pydantic models for detailed dataset column information.
No application imports — self-contained data schema.
"""

from pydantic import BaseModel


class ColumnInfo(BaseModel):
    """Information about a single dataset column."""

    name: str
    dtype: str
    non_null_count: int
    null_count: int
    unique_values: int

    model_config = {"extra": "forbid"}


class DatasetInfo(BaseModel):
    """Comprehensive dataset structural information."""

    total_rows: int
    total_columns: int
    columns: list[ColumnInfo]
    memory_usage_mb: float
    has_duplicates: bool
    duplicate_count: int

    model_config = {"extra": "forbid"}
