from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="viewer")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DatabaseConnection(Base):
    __tablename__ = "connections"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    dialect: Mapped[str] = mapped_column(String(20))
    encrypted_url: Mapped[str] = mapped_column(Text)
    read_only_status: Mapped[str] = mapped_column(String(20), default="unknown")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class WorkspaceSettings(Base):
    __tablename__ = "workspace_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    llm_provider: Mapped[str] = mapped_column(String(30), default="ollama")
    llm_model: Mapped[str] = mapped_column(String(100), default="qwen2.5-coder:7b")
    encrypted_llm_api_key: Mapped[str] = mapped_column(Text, default="")
    llm_base_url: Mapped[str] = mapped_column(Text, default="")
    cloud_summaries_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    pii_redaction_enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class SchemaPermission(Base):
    __tablename__ = "schema_permissions"
    __table_args__ = (
        UniqueConstraint(
            "connection_id",
            "role",
            "table_name",
            "column_name",
            name="uq_schema_permission",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("connections.id"), index=True)
    role: Mapped[str] = mapped_column(String(20), index=True)
    table_name: Mapped[str] = mapped_column(String(255))
    column_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    visible: Mapped[bool] = mapped_column(Boolean, default=True)


class SchemaAnnotation(Base):
    __tablename__ = "schema_annotations"
    __table_args__ = (
        UniqueConstraint(
            "connection_id",
            "table_name",
            "column_name",
            name="uq_schema_annotation",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("connections.id"), index=True)
    table_name: Mapped[str] = mapped_column(String(255))
    column_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text)


class VerifiedExample(Base):
    __tablename__ = "verified_examples"

    id: Mapped[int] = mapped_column(primary_key=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("connections.id"), index=True)
    question: Mapped[str] = mapped_column(Text)
    sql: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(20))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    audit_event_id: Mapped[int] = mapped_column(ForeignKey("audit_events.id"))


class FeedbackEvent(Base):
    __tablename__ = "feedback_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    audit_event_id: Mapped[int] = mapped_column(ForeignKey("audit_events.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    verdict: Mapped[str] = mapped_column(String(10))
    issue: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("connections.id"), index=True)
    question: Mapped[str] = mapped_column(Text)
    sql: Mapped[str | None] = mapped_column(Text, nullable=True)
    tables_touched: Mapped[list[str]] = mapped_column(JSON, default=list)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    provider: Mapped[str] = mapped_column(String(30))
    model: Mapped[str] = mapped_column(String(100))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    outcome: Mapped[str] = mapped_column(String(20), index=True)
    blocked_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    summary_sent_to_cloud: Mapped[bool] = mapped_column(Boolean, default=False)
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
