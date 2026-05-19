"""
PostgreSQL SQLAlchemy ORM models.

display_name on Dataset is NOT NULL — the upload API enforces this
at the application level (Form field is required) and at the DB level here.
"""

import datetime
import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from src.app.db.database import Base


class Dataset(Base):
    """
    Stores dataset schema metadata and the raw CSV bytes.

    display_name is unique and NOT NULL — it is the human-readable workspace
    label chosen by the user at upload time.
    """

    __tablename__ = "datasets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String, nullable=False)
    display_name = Column(String, unique=True, nullable=False)  # Mandatory, user-defined
    schema_json = Column(JSONB, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    raw_data = Column(LargeBinary, nullable=False)  # CSV bytes stored in DB
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)

    dashboard = relationship("Dashboard", back_populates="dataset", uselist=False)
    chat_history = relationship(
        "ChatMessage", back_populates="dataset", cascade="all, delete-orphan"
    )


class Dashboard(Base):
    """
    Stores dashboard configurations (layout) — one per dataset version snapshot.
    """

    __tablename__ = "dashboards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String, nullable=False)
    layout_json = Column(JSONB, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    active_version = Column(Integer, default=1, nullable=False)
    last_layout_update = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    dataset = relationship("Dataset", back_populates="dashboard")
    components = relationship(
        "DashboardComponent", back_populates="dashboard", cascade="all, delete-orphan"
    )


class DashboardComponent(Base):
    """
    A single widget/chart on a dashboard — stores position and chart schema.
    """

    __tablename__ = "dashboard_components"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dashboard_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dashboards.id", ondelete="CASCADE"),
        nullable=False,
    )
    query_plan = Column(JSONB, nullable=True)
    position = Column(JSONB, nullable=False)
    component_type = Column(String, nullable=False)  # "chart" | "insight"
    chart_schema = Column(JSONB, nullable=True)      # Agent-generated schema

    dashboard = relationship("Dashboard", back_populates="components")


class QueryLog(Base):
    """
    Logs queries executed by the system or agent for debugging and audit.
    """

    __tablename__ = "query_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="SET NULL"),
        nullable=True,
    )
    plan = Column(JSONB, nullable=False)
    execution_time_ms = Column(Float, nullable=False)
    status = Column(String, nullable=False)      # "success" | "failed"
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class ChatMessage(Base):
    """
    Persistent chat history linked to a dataset workspace.
    """

    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    role = Column(String, nullable=False)          # "user" | "assistant"
    content = Column(String, nullable=False)
    chart_schema = Column(JSONB, nullable=True)
    execution_time_ms = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    dataset = relationship("Dataset", back_populates="chat_history")


class SemanticDefinition(Base):
    """
    Semantic definitions: chart templates, metrics, dimensions.
    Seeded at startup from prompts.chart_templates.CHART_TEMPLATE_SEEDS.
    """

    __tablename__ = "semantic_definitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    definition_type = Column(String, nullable=False)  # "chart_template" | "metric" | etc.
    name = Column(String, nullable=False, unique=True)
    definition_json = Column(JSONB, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )
