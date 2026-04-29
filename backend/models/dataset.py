"""
Pydantic models for dataset information.
"""

from pydantic import BaseModel, Field


class ColumnInfo(BaseModel):
    """Information about a single dataset column."""

    name: str
    dtype: str
    non_null_count: int
    null_count: int
    unique_values: int

    class Config:
        extra = "forbid"


class DatasetInfo(BaseModel):
    """Comprehensive dataset information."""

    total_rows: int
    total_columns: int
    columns: list[ColumnInfo]
    memory_usage_mb: float
    has_duplicates: bool
    duplicate_count: int

    class Config:
        extra = "forbid"
