"""
Database configuration, session management, and schema initialisation.

- Engine and session factory configured from settings.POSTGRES_URI
- init_db() creates tables, runs safe schema migrations, and seeds chart templates
- CHART_TEMPLATE_SEEDS imported from prompts.chart_templates (no data in this file)
- logger used throughout — no print() calls
"""

import uuid
import logging
from typing import AsyncGenerator

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from src.app.config.settings import get_settings
from src.app.prompts.chart_templates import CHART_TEMPLATE_SEEDS

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Engine & session factory ──────────────────────────────────────────────────

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


# ── Session dependency ────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an async database session per request."""
    async with AsyncSessionLocal() as session:
        yield session


# ── Database initialisation ───────────────────────────────────────────────────

async def init_db() -> None:
    """
    Initialise the database on application startup.

    Steps:
    1. Create all tables defined in the ORM models (idempotent).
    2. Run safe ALTER TABLE migrations for columns added after initial deployment.
    3. Seed chart templates into semantic_definitions if the table is empty.
    """
    # Import models here to avoid circular imports at module level
    from src.app.db.models import SemanticDefinition  # noqa: PLC0415

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("ORM tables verified / created")

        # ── Schema evolution: add columns that may be missing on existing DBs ──
        await _ensure_column(
            conn,
            table="dashboards",
            column="dataset_id",
            ddl="ALTER TABLE dashboards ADD COLUMN dataset_id UUID REFERENCES datasets(id) ON DELETE CASCADE",
        )
        await _ensure_column(
            conn,
            table="dashboards",
            column="active_version",
            ddl="ALTER TABLE dashboards ADD COLUMN active_version INTEGER DEFAULT 1",
        )
        await _ensure_column(
            conn,
            table="dashboards",
            column="last_layout_update",
            ddl="ALTER TABLE dashboards ADD COLUMN last_layout_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        )
        await _ensure_column(
            conn,
            table="datasets",
            column="display_name",
            ddl="ALTER TABLE datasets ADD COLUMN display_name VARCHAR UNIQUE NOT NULL DEFAULT ''",
        )

    # ── Seed chart templates ──────────────────────────────────────────────────
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(SemanticDefinition).filter(
                SemanticDefinition.definition_type == "chart_template"
            )
        )
        existing = result.scalars().all()

        if not existing:
            logger.info("Seeding chart templates into semantic_definitions...")
            for seed in CHART_TEMPLATE_SEEDS:
                session.add(
                    SemanticDefinition(
                        id=uuid.uuid4(),
                        definition_type="chart_template",
                        name=seed["name"],
                        definition_json=seed["definition_json"],
                        version=1,
                    )
                )
            await session.commit()
            logger.info(f"Seeded {len(CHART_TEMPLATE_SEEDS)} chart templates")
        else:
            logger.info(
                f"Chart templates already exist ({len(existing)} found) — skipping seed"
            )


async def _ensure_column(conn, table: str, column: str, ddl: str) -> None:
    """
    Safely add a column to a table if it does not already exist.

    Uses information_schema to check for existence before running ALTER TABLE,
    making it safe to run on every startup against an already-migrated DB.
    """
    result = await conn.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = :table AND column_name = :column"
        ),
        {"table": table, "column": column},
    )
    if not result.fetchone():
        logger.info(f"Migration: adding column '{column}' to table '{table}'")
        await conn.execute(text(ddl))
    else:
        logger.debug(f"Column '{column}' on '{table}' already exists — skipping")
