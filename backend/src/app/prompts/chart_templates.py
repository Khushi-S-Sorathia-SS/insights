"""
Chart template seed data.

Defines the JSON schema the AI agent must follow for each supported chart type.
Extracted from database.py so it is a pure data module with no DB dependency.
The database's init_db() imports this and seeds the semantic_definitions table.
"""

from typing import Any

CHART_TEMPLATE_SEEDS: list[dict[str, Any]] = [
    {
        "name": "bar",
        "definition_json": {
            "type": "bar",
            "description": "Bar chart for comparing categories",
            "required_fields": {
                "type": "bar",
                "title": "string - descriptive title",
                "data": "array of objects with category and value keys",
                "xAxis": "string - key name for category axis",
                "yAxis": "string - key name for value axis",
            },
            "example": {
                "type": "bar",
                "title": "Sales by Region",
                "data": [
                    {"region": "North", "sales": 100},
                    {"region": "South", "sales": 200},
                ],
                "xAxis": "region",
                "yAxis": "sales",
            },
        },
    },
    {
        "name": "pie",
        "definition_json": {
            "type": "pie",
            "description": "Pie chart for showing proportions",
            "required_fields": {
                "type": "pie",
                "title": "string - descriptive title",
                "data": "array of objects with name and value keys",
                "xAxis": "string - key name for label",
                "yAxis": "string - key name for value",
            },
            "example": {
                "type": "pie",
                "title": "Distribution",
                "data": [
                    {"name": "A", "value": 30},
                    {"name": "B", "value": 70},
                ],
                "xAxis": "name",
                "yAxis": "value",
            },
        },
    },
    {
        "name": "line",
        "definition_json": {
            "type": "line",
            "description": "Line chart for trends over time",
            "required_fields": {
                "type": "line",
                "title": "string - descriptive title",
                "data": "array of objects with x and y keys",
                "xAxis": "string - key for x axis",
                "yAxis": "string - key for y axis",
            },
            "example": {
                "type": "line",
                "title": "Trend",
                "data": [
                    {"month": "Jan", "count": 10},
                    {"month": "Feb", "count": 20},
                ],
                "xAxis": "month",
                "yAxis": "count",
            },
        },
    },
    {
        "name": "area",
        "definition_json": {
            "type": "area",
            "description": "Area chart for cumulative trends",
            "required_fields": {
                "type": "area",
                "title": "string - descriptive title",
                "data": "array of objects",
                "xAxis": "string - key for x axis",
                "yAxis": "string - key for y axis",
            },
            "example": {
                "type": "area",
                "title": "Growth",
                "data": [
                    {"year": "2020", "revenue": 100},
                    {"year": "2021", "revenue": 150},
                ],
                "xAxis": "year",
                "yAxis": "revenue",
            },
        },
    },
    {
        "name": "scatter",
        "definition_json": {
            "type": "scatter",
            "description": "Scatter plot for correlations",
            "required_fields": {
                "type": "scatter",
                "title": "string - descriptive title",
                "data": "array of objects with x and y keys",
                "xAxis": "string - key for x axis",
                "yAxis": "string - key for y axis",
            },
            "example": {
                "type": "scatter",
                "title": "Correlation",
                "data": [
                    {"x": 5, "y": 85000},
                    {"x": 3, "y": 72000},
                ],
                "xAxis": "x",
                "yAxis": "y",
            },
        },
    },
    {
        "name": "radar",
        "definition_json": {
            "type": "radar",
            "description": "Radar chart for multi-dimensional comparison",
            "required_fields": {
                "type": "radar",
                "title": "string - descriptive title",
                "data": "array of objects with dimension and value keys",
                "xAxis": "string - key for dimension",
                "yAxis": "string - key for value",
            },
            "example": {
                "type": "radar",
                "title": "Skill Comparison",
                "data": [
                    {"skill": "Python", "score": 90},
                    {"skill": "SQL", "score": 80},
                ],
                "xAxis": "skill",
                "yAxis": "score",
            },
        },
    },
    {
        "name": "donut",
        "definition_json": {
            "type": "donut",
            "description": "Donut chart for showing proportions in a ring",
            "required_fields": {
                "type": "donut",
                "title": "string - descriptive title",
                "data": "array of objects with name and value keys",
                "xAxis": "string - key name for label",
                "yAxis": "string - key name for value",
            },
            "example": {
                "type": "donut",
                "title": "Distribution",
                "data": [
                    {"name": "A", "value": 30},
                    {"name": "B", "value": 70},
                ],
                "xAxis": "name",
                "yAxis": "value",
            },
        },
    },
]
