import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.auth import current_user, require_role
from app.db.models import AuditEvent, User
from app.db.session import get_db

router = APIRouter(prefix="/api/audit", tags=["audit"])


class AuditEventResponse(BaseModel):
    id: int
    ts: datetime
    user_id: int
    connection_id: int
    question: str
    sql: str | None
    tables_touched: list[str]
    row_count: int
    duration_ms: int
    provider: str
    model: str
    attempts: int
    outcome: str
    blocked_reason: str | None
    summary_sent_to_cloud: bool

    model_config = ConfigDict(from_attributes=True)


class AuditPage(BaseModel):
    items: list[AuditEventResponse]
    total: int
    page: int
    page_size: int


def _filters(
    statement: Select[tuple[AuditEvent]],
    *,
    user_id: int | None = None,
    connection_id: int | None = None,
    outcome: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
) -> Select[tuple[AuditEvent]]:
    if user_id is not None:
        statement = statement.where(AuditEvent.user_id == user_id)
    if connection_id is not None:
        statement = statement.where(AuditEvent.connection_id == connection_id)
    if outcome:
        statement = statement.where(AuditEvent.outcome == outcome)
    if from_date:
        statement = statement.where(AuditEvent.ts >= from_date)
    if to_date:
        statement = statement.where(AuditEvent.ts <= to_date)
    return statement


@router.get("", response_model=AuditPage)
def audit_log(
    user_id: int | None = None,
    connection_id: int | None = None,
    outcome: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    export_format: str | None = Query(None, alias="format"),
    _admin: User = Depends(require_role("admin")),
    database: Session = Depends(get_db),
):
    statement = _filters(
        select(AuditEvent),
        user_id=user_id,
        connection_id=connection_id,
        outcome=outcome,
        from_date=from_date,
        to_date=to_date,
    ).order_by(AuditEvent.ts.desc())
    if export_format == "csv":
        events = list(database.scalars(statement))
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(AuditEventResponse.model_fields)
        for event in events:
            writer.writerow(AuditEventResponse.model_validate(event).model_dump().values())
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=audit.csv"},
        )

    count_statement = select(func.count()).select_from(statement.order_by(None).subquery())
    total = database.scalar(count_statement) or 0
    events = list(database.scalars(statement.offset((page - 1) * page_size).limit(page_size)))
    return AuditPage(
        items=[AuditEventResponse.model_validate(event) for event in events],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/me", response_model=AuditPage)
def my_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user: User = Depends(current_user),
    database: Session = Depends(get_db),
) -> AuditPage:
    statement = (
        select(AuditEvent)
        .where(AuditEvent.user_id == user.id)
        .order_by(AuditEvent.ts.desc())
    )
    total = database.scalar(
        select(func.count()).select_from(AuditEvent).where(AuditEvent.user_id == user.id)
    ) or 0
    events = list(database.scalars(statement.offset((page - 1) * page_size).limit(page_size)))
    return AuditPage(
        items=[AuditEventResponse.model_validate(event) for event in events],
        total=total,
        page=page,
        page_size=page_size,
    )
