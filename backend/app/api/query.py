from time import perf_counter
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import write_audit_event
from app.connectors.factory import connector_from_record
from app.core.auth import current_user
from app.db.models import DatabaseConnection, SchemaAnnotation, SchemaPermission, User
from app.db.session import get_db
from app.knowledge.store import get_knowledge_store
from app.llm.service import resolve_llm
from app.pipeline.graph import build_pipeline
from app.pipeline.state import HistoryTurn
from app.settings import Settings, get_settings

router = APIRouter(prefix="/api/query", tags=["query"])


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2_000)
    connection_id: int
    history: list[HistoryTurn] = Field(default_factory=list, max_length=3)


class QueryResponse(BaseModel):
    audit_event_id: int
    question: str
    sql: str | None
    columns: list[str]
    rows: list[list[Any]]
    summary: str | None
    summary_reason: str | None
    followups: list[str]
    tables_touched: list[str]
    attempts: int
    unanswerable: bool
    unanswerable_reason: str | None
    duration_ms: int
    grounded_on_count: int


@router.post("", response_model=QueryResponse)
async def run_query(
    payload: QueryRequest,
    user: User = Depends(current_user),
    database: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> QueryResponse:
    connection = database.get(DatabaseConnection, payload.connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")

    connector = connector_from_record(connection, settings)
    llm = resolve_llm(database, settings)
    permissions = list(
        database.scalars(
            select(SchemaPermission).where(
                SchemaPermission.connection_id == connection.id,
                SchemaPermission.role == user.role,
            )
        )
    )
    annotations = list(
        database.scalars(
            select(SchemaAnnotation).where(
                SchemaAnnotation.connection_id == connection.id
            )
        )
    )
    started_at = perf_counter()
    state: dict[str, Any] = {}
    try:
        state = await build_pipeline().ainvoke(
            {
                "question": payload.question,
                "connector": connector,
                "llm": llm.client,
                "role": user.role,
                "permissions": permissions,
                "annotations": annotations,
                "connection_id": connection.id,
                "knowledge_store": get_knowledge_store(),
                "attempt": 0,
                "max_attempts": settings.query_max_attempts,
                "max_rows": settings.query_max_rows,
                "history": payload.history,
                "summaries_enabled": llm.summaries_enabled,
                "redact_before_summary": (
                    llm.provider != "ollama" and llm.pii_redaction_enabled
                ),
            }
        )
        validation = state.get("validation")
        blocked_reason = validation.reason if validation and not validation.ok else None
        outcome = (
            "blocked"
            if blocked_reason == "table_not_allowed"
            else "error"
            if state.get("error")
            else "unanswerable"
            if state.get("unanswerable")
            else "ok"
        )
    except Exception as exc:
        outcome = "error"
        blocked_reason = None
        state = {"error": str(exc), "unanswerable_reason": "The query could not be completed."}

    duration_ms = round((perf_counter() - started_at) * 1000)
    validation = state.get("validation")
    audit_tables = validation.tables if validation else []
    response_tables = [] if blocked_reason == "table_not_allowed" else audit_tables
    rows = state.get("rows", [])
    event = write_audit_event(
        database,
        user_id=user.id,
        connection_id=connection.id,
        question=payload.question,
        sql=state.get("sql"),
        tables_touched=audit_tables,
        row_count=len(rows),
        duration_ms=duration_ms,
        provider=llm.provider,
        model=llm.model,
        attempts=state.get("attempt", 0),
        outcome=outcome,
        blocked_reason=blocked_reason,
        summary_sent_to_cloud=(
            llm.provider != "ollama" and state.get("summary") is not None
        ),
    )
    followups = state.get("followups", [])
    if state.get("unanswerable") and not followups:
        followups = [
            f"What information is available in {table}?"
            for table in state.get("schema_tables", [])[:3]
        ]
    return QueryResponse(
        audit_event_id=event.id,
        question=payload.question,
        sql=None if blocked_reason == "table_not_allowed" else state.get("sql"),
        columns=state.get("columns", []),
        rows=rows,
        summary=state.get("summary"),
        summary_reason=state.get("summary_reason"),
        followups=followups,
        tables_touched=response_tables,
        attempts=state.get("attempt", 0),
        unanswerable=bool(state.get("unanswerable") or outcome in {"blocked", "error"}),
        unanswerable_reason=state.get("unanswerable_reason") or state.get("error"),
        duration_ms=duration_ms,
        grounded_on_count=len(state.get("grounded_on", [])),
    )
