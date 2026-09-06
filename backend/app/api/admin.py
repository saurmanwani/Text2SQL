from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.connectors.base import TableModel
from app.connectors.factory import connector_from_record
from app.core.auth import require_role
from app.core.crypto import encrypt_value
from app.db.models import (
    AuditEvent,
    DatabaseConnection,
    FeedbackEvent,
    SchemaAnnotation,
    SchemaPermission,
    User,
    VerifiedExample,
    WorkspaceSettings,
)
from app.db.session import get_db
from app.knowledge.store import get_knowledge_store
from app.llm.providers import get_provider_preset
from app.safety.validator import validate
from app.settings import Settings, get_settings

router = APIRouter(prefix="/api/admin", tags=["admin"])


class AISettingsUpdate(BaseModel):
    llm_provider: str
    llm_model: str = ""
    llm_api_key: str = ""
    llm_base_url: str = ""
    cloud_summaries_enabled: bool = False
    pii_redaction_enabled: bool = True


class AISettingsResponse(BaseModel):
    llm_provider: str
    llm_model: str
    llm_base_url: str
    has_api_key: bool
    cloud_summaries_enabled: bool
    pii_redaction_enabled: bool


class PermissionUpdate(BaseModel):
    role: str
    table_name: str
    column_name: str | None = None
    visible: bool


class SchemaConfigResponse(BaseModel):
    tables: list[TableModel]
    permissions: list[PermissionUpdate]


class AnnotationUpdate(BaseModel):
    table_name: str
    column_name: str | None = None
    description: str


class VerifiedExampleResponse(BaseModel):
    id: int
    connection_id: int
    question: str
    sql: str
    source: str
    created_by: int
    created_at: datetime
    audit_event_id: int

    model_config = ConfigDict(from_attributes=True)


class VerifiedExampleUpdate(BaseModel):
    sql: str


class WeeklyMetric(BaseModel):
    week: str
    queries: int
    thumbs_up_rate: float | None


class MetricsResponse(BaseModel):
    total_queries: int
    blocked_count: int
    weeks: list[WeeklyMetric]


def _workspace(database: Session) -> WorkspaceSettings:
    workspace = database.get(WorkspaceSettings, 1)
    if workspace is None:
        workspace = WorkspaceSettings(id=1)
        database.add(workspace)
        database.commit()
        database.refresh(workspace)
    return workspace


def _ai_response(workspace: WorkspaceSettings) -> AISettingsResponse:
    return AISettingsResponse(
        llm_provider=workspace.llm_provider,
        llm_model=workspace.llm_model,
        llm_base_url=workspace.llm_base_url,
        has_api_key=bool(workspace.encrypted_llm_api_key),
        cloud_summaries_enabled=workspace.cloud_summaries_enabled,
        pii_redaction_enabled=workspace.pii_redaction_enabled,
    )


@router.get("/ai", response_model=AISettingsResponse)
def get_ai_settings(
    _admin: User = Depends(require_role("admin")),
    database: Session = Depends(get_db),
) -> AISettingsResponse:
    return _ai_response(_workspace(database))


@router.put("/ai", response_model=AISettingsResponse)
def update_ai_settings(
    payload: AISettingsUpdate,
    _admin: User = Depends(require_role("admin")),
    database: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AISettingsResponse:
    preset = get_provider_preset(payload.llm_provider)
    workspace = _workspace(database)
    workspace.llm_provider = payload.llm_provider
    workspace.llm_model = payload.llm_model or preset.default_model
    workspace.llm_base_url = payload.llm_base_url
    workspace.cloud_summaries_enabled = (
        False if payload.llm_provider == "ollama" else payload.cloud_summaries_enabled
    )
    workspace.pii_redaction_enabled = payload.pii_redaction_enabled
    if payload.llm_api_key:
        workspace.encrypted_llm_api_key = encrypt_value(payload.llm_api_key, settings.app_secret)
    database.commit()
    return _ai_response(workspace)


@router.get("/schema/{connection_id}", response_model=SchemaConfigResponse)
def get_schema_config(
    connection_id: int,
    _admin: User = Depends(require_role("admin")),
    database: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SchemaConfigResponse:
    connection = database.get(DatabaseConnection, connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")
    tables = connector_from_record(connection, settings).get_schema().tables
    annotations = list(
        database.scalars(
            select(SchemaAnnotation).where(
                SchemaAnnotation.connection_id == connection_id
            )
        )
    )
    annotation_map = {
        (item.table_name, item.column_name): item.description for item in annotations
    }
    for table in tables:
        table.description = annotation_map.get((table.name, None), "")
        for column in table.columns:
            column.description = annotation_map.get((table.name, column.name), "")
    permissions = database.scalars(
        select(SchemaPermission).where(SchemaPermission.connection_id == connection_id)
    )
    return SchemaConfigResponse(
        tables=tables,
        permissions=[
            PermissionUpdate(
                role=permission.role,
                table_name=permission.table_name,
                column_name=permission.column_name,
                visible=permission.visible,
            )
            for permission in permissions
        ],
    )


@router.put("/schema/{connection_id}", response_model=SchemaConfigResponse)
def update_schema_config(
    connection_id: int,
    updates: list[PermissionUpdate],
    _admin: User = Depends(require_role("admin")),
    database: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SchemaConfigResponse:
    if database.get(DatabaseConnection, connection_id) is None:
        raise HTTPException(status_code=404, detail="Connection not found")
    for update in updates:
        if update.role not in {"analyst", "viewer"}:
            raise HTTPException(
                status_code=422,
                detail="Only analyst and viewer visibility can change",
            )
        database.execute(
            delete(SchemaPermission).where(
                SchemaPermission.connection_id == connection_id,
                SchemaPermission.role == update.role,
                SchemaPermission.table_name == update.table_name,
                SchemaPermission.column_name == update.column_name,
            )
        )
        database.add(SchemaPermission(connection_id=connection_id, **update.model_dump()))
    database.commit()
    return get_schema_config(connection_id, _admin, database, settings)


@router.put("/schema/{connection_id}/annotations", response_model=list[AnnotationUpdate])
def update_annotations(
    connection_id: int,
    updates: list[AnnotationUpdate],
    _admin: User = Depends(require_role("admin")),
    database: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[AnnotationUpdate]:
    connection = database.get(DatabaseConnection, connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")
    for update in updates:
        database.execute(
            delete(SchemaAnnotation).where(
                SchemaAnnotation.connection_id == connection_id,
                SchemaAnnotation.table_name == update.table_name,
                SchemaAnnotation.column_name == update.column_name,
            )
        )
        if update.description.strip():
            database.add(
                SchemaAnnotation(
                    connection_id=connection_id,
                    **update.model_dump(),
                )
            )
    database.commit()
    reindex_knowledge(connection_id, _admin, database, settings)
    return updates


@router.post("/knowledge/reindex/{connection_id}")
def reindex_knowledge(
    connection_id: int,
    _admin: User = Depends(require_role("admin")),
    database: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    connection = database.get(DatabaseConnection, connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")
    schema = connector_from_record(connection, settings).get_schema()
    annotations = list(
        database.scalars(
            select(SchemaAnnotation).where(
                SchemaAnnotation.connection_id == connection_id
            )
        )
    )
    get_knowledge_store().reindex_schema(connection_id, schema, annotations)
    return {"status": "indexed"}


@router.get("/library", response_model=list[VerifiedExampleResponse])
def verified_library(
    search: str | None = None,
    _admin: User = Depends(require_role("admin")),
    database: Session = Depends(get_db),
) -> list[VerifiedExampleResponse]:
    statement = select(VerifiedExample).order_by(VerifiedExample.created_at.desc())
    if search:
        statement = statement.where(VerifiedExample.question.ilike(f"%{search}%"))
    return [
        VerifiedExampleResponse.model_validate(example)
        for example in database.scalars(statement)
    ]


@router.put("/library/{example_id}", response_model=VerifiedExampleResponse)
def update_verified_example(
    example_id: int,
    payload: VerifiedExampleUpdate,
    _admin: User = Depends(require_role("admin")),
    database: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> VerifiedExampleResponse:
    example = database.get(VerifiedExample, example_id)
    if example is None:
        raise HTTPException(status_code=404, detail="Example not found")
    connection = database.get(DatabaseConnection, example.connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")
    connector = connector_from_record(connection, settings)
    schema = connector.get_schema()
    result = validate(
        payload.sql,
        connector.dialect,
        {table.name for table in schema.tables},
        settings.query_max_rows,
    )
    if not result.ok or not result.sql:
        raise HTTPException(status_code=422, detail=result.reason or "Invalid SQL")
    connector.execute(result.sql, settings.query_max_rows)
    example.sql = result.sql
    database.commit()
    database.refresh(example)
    get_knowledge_store().upsert_example(example)
    return VerifiedExampleResponse.model_validate(example)


@router.delete("/library/{example_id}", status_code=204)
def delete_verified_example(
    example_id: int,
    _admin: User = Depends(require_role("admin")),
    database: Session = Depends(get_db),
) -> None:
    example = database.get(VerifiedExample, example_id)
    if example is None:
        raise HTTPException(status_code=404, detail="Example not found")
    get_knowledge_store().delete_example(example.connection_id, example.id)
    database.delete(example)
    database.commit()


@router.get("/metrics", response_model=MetricsResponse)
def admin_metrics(
    _admin: User = Depends(require_role("admin")),
    database: Session = Depends(get_db),
) -> MetricsResponse:
    audits = list(database.scalars(select(AuditEvent)))
    feedback = list(database.scalars(select(FeedbackEvent)))
    feedback_by_audit = {item.audit_event_id: item.verdict for item in feedback}
    by_week: dict[str, list[AuditEvent]] = {}
    for audit in audits:
        week = audit.ts.strftime("%Y-W%W")
        by_week.setdefault(week, []).append(audit)
    weeks = []
    for week, events in sorted(by_week.items()):
        verdicts = [
            feedback_by_audit[event.id]
            for event in events
            if event.id in feedback_by_audit
        ]
        positive = verdicts.count("up")
        weeks.append(
            WeeklyMetric(
                week=week,
                queries=len(events),
                thumbs_up_rate=(positive / len(verdicts)) if verdicts else None,
            )
        )
    return MetricsResponse(
        total_queries=len(audits),
        blocked_count=sum(audit.outcome == "blocked" for audit in audits),
        weeks=weeks,
    )
