from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.factory import connector_from_record
from app.core.auth import current_user
from app.db.models import (
    AuditEvent,
    DatabaseConnection,
    FeedbackEvent,
    SchemaPermission,
    User,
    VerifiedExample,
)
from app.db.session import get_db
from app.knowledge.store import get_knowledge_store
from app.knowledge.visibility import filter_schema
from app.safety.validator import validate
from app.settings import Settings, get_settings

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    audit_event_id: int
    verdict: Literal["up", "down"]
    issue: str | None = None
    corrected_sql: str | None = None


class FeedbackResponse(BaseModel):
    saved: bool
    example_id: int | None = None
    columns: list[str] = Field(default_factory=list)
    rows: list[list[Any]] = Field(default_factory=list)


@router.post("", response_model=FeedbackResponse)
def submit_feedback(
    payload: FeedbackRequest,
    user: User = Depends(current_user),
    database: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> FeedbackResponse:
    audit = database.get(AuditEvent, payload.audit_event_id)
    if audit is None or audit.user_id != user.id:
        raise HTTPException(status_code=404, detail="Query not found")
    database.add(
        FeedbackEvent(
            audit_event_id=audit.id,
            user_id=user.id,
            verdict=payload.verdict,
            issue=payload.issue,
        )
    )

    sql: str | None = None
    source = "thumbs_up"
    columns: list[str] = []
    rows: list[list[Any]] = []
    if payload.verdict == "up":
        if audit.outcome != "ok" or not audit.sql:
            raise HTTPException(status_code=422, detail="Only successful queries can be verified")
        sql = audit.sql
    elif payload.corrected_sql:
        source = "correction"
        connection = database.get(DatabaseConnection, audit.connection_id)
        if connection is None:
            raise HTTPException(status_code=404, detail="Connection not found")
        connector = connector_from_record(connection, settings)
        permissions = list(
            database.scalars(
                select(SchemaPermission).where(
                    SchemaPermission.connection_id == connection.id,
                    SchemaPermission.role == user.role,
                )
            )
        )
        visible_schema = filter_schema(connector.get_schema(), user.role, permissions)
        validation = validate(
            payload.corrected_sql,
            connector.dialect,
            {table.name for table in visible_schema.tables},
            settings.query_max_rows,
        )
        if not validation.ok or not validation.sql:
            raise HTTPException(status_code=422, detail=validation.reason or "Invalid SQL")
        result = connector.execute(validation.sql, settings.query_max_rows)
        sql = validation.sql
        columns = result.columns
        rows = result.rows

    if sql is None:
        database.commit()
        return FeedbackResponse(saved=True)

    example = VerifiedExample(
        connection_id=audit.connection_id,
        question=audit.question,
        sql=sql,
        source=source,
        created_by=user.id,
        audit_event_id=audit.id,
    )
    database.add(example)
    database.commit()
    database.refresh(example)
    get_knowledge_store().upsert_example(example)
    return FeedbackResponse(
        saved=True,
        example_id=example.id,
        columns=columns,
        rows=rows,
    )
