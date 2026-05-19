"""
Dashboard helper — utility class for inspecting chart schemas inside the sandbox.

This file is also uploaded to the Daytona sandbox by agent_planner.py so the
agent can call helper.find_widgets_by_type() etc. inside the sandboxed Python
environment. It must therefore have NO imports from the rest of the application.
"""

import json
from typing import Dict, List, Optional


class DashboardHelper:
    """Lightweight helper for finding widgets in a dashboard schema file."""

    def __init__(self, schemas_path: str = "/home/daytona/dashboard_schemas.json") -> None:
        self.schemas_path = schemas_path
        self._schemas: Optional[List[Dict]] = None

    def load_dashboard_schemas(self) -> List[Dict]:
        """Load and cache the full dashboard schemas from the sandbox file."""
        if self._schemas is None:
            try:
                with open(self.schemas_path, "r", encoding="utf-8") as f:
                    self._schemas = json.load(f)
            except FileNotFoundError:
                # Logged here without app logger — this runs inside the sandbox
                print(f"Warning: Schema file not found at {self.schemas_path}")
                self._schemas = []
            except json.JSONDecodeError:
                print(f"Error: Failed to parse schema file at {self.schemas_path}")
                self._schemas = []
        return self._schemas

    def get_widget_by_id(self, widget_id: str) -> Optional[Dict]:
        """Find a widget by its exact UUID."""
        schemas = self.load_dashboard_schemas()
        for widget in schemas:
            if widget.get("id") == widget_id:
                return widget
        return None

    def find_widgets_by_title(self, search_text: str, exact: bool = False) -> List[Dict]:
        """Find widgets whose title contains or exactly matches search_text."""
        schemas = self.load_dashboard_schemas()
        search_lower = search_text.lower()
        results = []
        for widget in schemas:
            schema = widget.get("schema", {})
            title = str(schema.get("title", "") if schema else "").lower()
            if exact and search_lower == title:
                results.append(widget)
            elif not exact and search_lower in title:
                results.append(widget)
        return results

    def find_widgets_by_type(self, chart_type: str) -> List[Dict]:
        """Find all widgets of a specific chart type (e.g., 'pie', 'bar', 'line')."""
        schemas = self.load_dashboard_schemas()
        chart_type_lower = chart_type.lower()
        results = []
        for widget in schemas:
            schema = widget.get("schema", {})
            actual_type = str(
                schema.get("type", "") if schema else widget.get("component_type", "")
            ).lower()
            if actual_type == chart_type_lower:
                results.append(widget)
        return results


# Module-level instance for convenient import inside the sandbox
helper = DashboardHelper()
