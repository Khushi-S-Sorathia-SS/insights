"""
Semantic Layer for fetching and validating definitions.
"""

import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db.models import SemanticDefinition

async def get_chart_rules(db: AsyncSession) -> str:
    """
    Fetches all chart templates from the database and formats them as a string 
    for the agent to understand the supported schemas.
    """
    result = await db.execute(
        select(SemanticDefinition).filter(SemanticDefinition.definition_type == 'chart_template')
    )
    templates = result.scalars().all()
    
    if not templates:
        # Fallback if DB is empty, though init_db should populate this.
        return "No specific chart rules defined in DB. Use generic representations."
        
    rules = []
    for template in templates:
        rules.append(f"Chart Type: '{template.name}'\nSchema Required:\n{json.dumps(template.definition_json, indent=2)}")
        
    return "\n\n".join(rules)
