"""
PostgreSQL SQLAlchemy Models.
"""

import datetime
import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, LargeBinary
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .database import Base


class Dataset(Base):
    """
    Stores dataset schema, version, and the raw CSV bytes.
    """
    __tablename__ = "datasets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String, nullable=False)
    schema_json = Column(JSONB, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    raw_data = Column(LargeBinary, nullable=False)  # Stores the CSV content directly
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)


class Dashboard(Base):
    """
    Stores dashboard configurations (layout).
    """
    __tablename__ = "dashboards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    layout_json = Column(JSONB, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    components = relationship("DashboardComponent", back_populates="dashboard", cascade="all, delete-orphan")


class DashboardComponent(Base):
    """
    Stores individual components/charts on a dashboard.
    """
    __tablename__ = "dashboard_components"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dashboard_id = Column(UUID(as_uuid=True), ForeignKey("dashboards.id", ondelete="CASCADE"), nullable=False)
    query_plan = Column(JSONB, nullable=True)
    position = Column(JSONB, nullable=False)
    component_type = Column(String, nullable=False)  # E.g. 'chart', 'table', 'text'
    chart_schema = Column(JSONB, nullable=True) # The actual chart output from agent planner

    dashboard = relationship("Dashboard", back_populates="components")


class QueryLog(Base):
    """
    Logs queries executed by the system/agent.
    """
    __tablename__ = "query_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True)
    plan = Column(JSONB, nullable=False)
    execution_time_ms = Column(Float, nullable=False)
    status = Column(String, nullable=False) # E.g., 'success', 'failed'
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class SemanticDefinition(Base):
    """
    Semantic definitions (metrics, dimensions, aliases).
    """
    __tablename__ = "semantic_definitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    definition_type = Column(String, nullable=False) # e.g., 'metric', 'dimension', 'chart_template'
    name = Column(String, nullable=False, unique=True)
    definition_json = Column(JSONB, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
