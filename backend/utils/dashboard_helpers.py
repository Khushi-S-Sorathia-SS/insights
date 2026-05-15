import json
from typing import List, Dict, Optional

class DashboardHelper:
    def __init__(self, schemas_path: str = "/home/daytona/dashboard_schemas.json"):
        self.schemas_path = schemas_path
        self._schemas = None

    def load_dashboard_schemas(self) -> List[Dict]:
        """Loads and caches the full dashboard schemas from the sandbox file."""
        if self._schemas is None:
            try:
                with open(self.schemas_path, "r") as f:
                    self._schemas = json.load(f)
            except FileNotFoundError:
                print(f"Warning: Schema file not found at {self.schemas_path}")
                self._schemas = []
            except json.JSONDecodeError:
                print(f"Error: Failed to parse schema file at {self.schemas_path}")
                self._schemas = []
        return self._schemas

    def get_widget_by_id(self, widget_id: str) -> Optional[Dict]:
        """Finds a widget by its exact UUID."""
        schemas = self.load_dashboard_schemas()
        for widget in schemas:
            if widget.get("id") == widget_id:
                return widget
        return None

    def find_widgets_by_title(self, search_text: str, exact: bool = False) -> List[Dict]:
        """Finds widgets whose title contains or matches the search_text."""
        schemas = self.load_dashboard_schemas()
        results = []
        search_lower = search_text.lower()
        
        for widget in schemas:
            schema = widget.get("schema", {})
            title = schema.get("title", "") if schema else ""
            title_lower = str(title).lower() if title else ""
            
            if exact and search_lower == title_lower:
                results.append(widget)
            elif not exact and search_lower in title_lower:
                results.append(widget)
                
        return results

    def find_widgets_by_type(self, chart_type: str) -> List[Dict]:
        """Finds widgets of a specific chart type (e.g., 'pie', 'bar', 'line')."""
        schemas = self.load_dashboard_schemas()
        results = []
        chart_type_lower = str(chart_type).lower()
        
        for widget in schemas:
            schema = widget.get("schema", {})
            actual_type = schema.get("type", "") if schema else widget.get("component_type", "")
            actual_type_lower = str(actual_type).lower() if actual_type else ""
            
            if actual_type_lower == chart_type_lower:
                results.append(widget)
                
        return results

# Provide a ready-to-use instance
helper = DashboardHelper()
