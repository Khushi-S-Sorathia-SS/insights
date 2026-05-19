"""
Semantic layer — fetches chart schema rules from the semantic_definitions table.
Used by the agent planner and upload route to inject chart format instructions.
"""

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.db.models import SemanticDefinition


async def get_chart_rules(db: AsyncSession) -> str:
    """
    Fetch all chart templates from the DB and format them as a prompt string.

    Returns a multi-section string where each section describes one chart type
    and its required JSON schema. The agent uses this to produce valid chart data.

    Falls back to a minimal message if the table is empty (should not happen
    after init_db() seeds the templates on startup).
    """
    result = await db.execute(
        select(SemanticDefinition).filter(
            SemanticDefinition.definition_type == "chart_template"
        )
    )
    templates = result.scalars().all()

    if not templates:
        return (
            "No specific chart rules defined in DB. "
            "Use generic chart representations."
        )

    rules = [
        f"Chart Type: '{template.name}'\n"
        f"Schema Required:\n{json.dumps(template.definition_json, indent=2)}"
        for template in templates
    ]
    return "\n\n".join(rules)
