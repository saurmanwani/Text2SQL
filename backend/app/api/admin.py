from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.connectors.base import TableModel
from app.connectors.factory import connector_from_record
from app.core.auth import require_role
from app.core.crypto import encrypt_value
from app.db.models import (
    DatabaseConnection,
    SchemaPermission,
    User,
    WorkspaceSettings,
)
from app.db.session import get_db
from app.llm.providers import get_provider_preset
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
