"""
Database configuration and session management.
"""

import uuid
import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy import select, text

from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

engine = create_async_engine(
    settings.POSTGRES_URI,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database session."""
    async with AsyncSessionLocal() as session:
        yield session


# Chart template seed data — defines the JSON schema the AI agent must follow for each chart type.
CHART_TEMPLATE_SEEDS = [
    {"name": "bar", "definition_json": {"type":"bar","description":"Bar chart for comparing categories","required_fields":{"type":"bar","title":"string - descriptive title","data":"array of objects with category and value keys","xAxis":"string - key name for category axis","yAxis":"string - key name for value axis"},"example":{"type":"bar","title":"Sales by Region","data":[{"region":"North","sales":100},{"region":"South","sales":200}],"xAxis":"region","yAxis":"sales"}}},
    {"name": "pie", "definition_json": {"type":"pie","description":"Pie chart for showing proportions","required_fields":{"type":"pie","title":"string - descriptive title","data":"array of objects with name and value keys","xAxis":"string - key name for label","yAxis":"string - key name for value"},"example":{"type":"pie","title":"Distribution","data":[{"name":"A","value":30},{"name":"B","value":70}],"xAxis":"name","yAxis":"value"}}},
    {"name": "line", "definition_json": {"type":"line","description":"Line chart for trends over time","required_fields":{"type":"line","title":"string - descriptive title","data":"array of objects with x and y keys","xAxis":"string - key for x axis","yAxis":"string - key for y axis"},"example":{"type":"line","title":"Trend","data":[{"month":"Jan","count":10},{"month":"Feb","count":20}],"xAxis":"month","yAxis":"count"}}},
    {"name": "area", "definition_json": {"type":"area","description":"Area chart for cumulative trends","required_fields":{"type":"area","title":"string - descriptive title","data":"array of objects","xAxis":"string - key for x axis","yAxis":"string - key for y axis"},"example":{"type":"area","title":"Growth","data":[{"year":"2020","revenue":100},{"year":"2021","revenue":150}],"xAxis":"year","yAxis":"revenue"}}},
    {"name": "scatter", "definition_json": {"type":"scatter","description":"Scatter plot for correlations","required_fields":{"type":"scatter","title":"string - descriptive title","data":"array of objects with x and y keys","xAxis":"string - key for x axis","yAxis":"string - key for y axis"},"example":{"type":"scatter","title":"Correlation","data":[{"x":5,"y":85000},{"x":3,"y":72000}],"xAxis":"x","yAxis":"y"}}},
    {"name": "radar", "definition_json": {"type":"radar","description":"Radar chart for multi-dimensional comparison","required_fields":{"type":"radar","title":"string - descriptive title","data":"array of objects with dimension and value keys","xAxis":"string - key for dimension","yAxis":"string - key for value"},"example":{"type":"radar","title":"Skill Comparison","data":[{"skill":"Python","score":90},{"skill":"SQL","score":80}],"xAxis":"skill","yAxis":"score"}}},
]


async def init_db():
    """Initialize the database (create tables) and seed chart templates."""
    # Import models here to avoid circular imports
    from .models import SemanticDefinition

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # Schema Evolution: Add missing columns to dashboards table if they don't exist
        print("Checking for schema updates...")
        # Check dataset_id
        result = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='dashboards' AND column_name='dataset_id'"))
        if not result.fetchone():
            print("Migration: Adding dataset_id to dashboards")
            await conn.execute(text("ALTER TABLE dashboards ADD COLUMN dataset_id UUID REFERENCES datasets(id) ON DELETE CASCADE"))
            
        # Check active_version
        result = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='dashboards' AND column_name='active_version'"))
        if not result.fetchone():
            print("Migration: Adding active_version to dashboards")
            await conn.execute(text("ALTER TABLE dashboards ADD COLUMN active_version INTEGER DEFAULT 1"))
            
        # Check last_layout_update
        result = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='dashboards' AND column_name='last_layout_update'"))
        if not result.fetchone():
            print("Migration: Adding last_layout_update to dashboards")
            await conn.execute(text("ALTER TABLE dashboards ADD COLUMN last_layout_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))

        # Check display_name in datasets
        result = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='datasets' AND column_name='display_name'"))
        if not result.fetchone():
            print("Migration: Adding display_name to datasets")
            await conn.execute(text("ALTER TABLE datasets ADD COLUMN display_name VARCHAR UNIQUE"))

    # Seed chart templates if the table is empty
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(SemanticDefinition).filter(SemanticDefinition.definition_type == 'chart_template')
        )
        existing = result.scalars().all()

        if not existing:
            logger.info("Seeding chart templates into semantic_definitions...")
            for seed in CHART_TEMPLATE_SEEDS:
                session.add(SemanticDefinition(
                    id=uuid.uuid4(),
                    definition_type='chart_template',
                    name=seed["name"],
                    definition_json=seed["definition_json"],
                    version=1,
                ))
            await session.commit()
            logger.info(f"Seeded {len(CHART_TEMPLATE_SEEDS)} chart templates.")
        else:
            logger.info(f"Chart templates already exist ({len(existing)} found). Skipping seed.")
