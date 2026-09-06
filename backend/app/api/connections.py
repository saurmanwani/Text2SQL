import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.factory import connector_from_record
from app.connectors.sqlalchemy_connector import SQLAlchemyConnector
from app.core.auth import current_user, require_role
from app.core.crypto import encrypt_value
from app.db.models import DatabaseConnection, User
from app.db.session import get_db
from app.settings import Settings, get_settings

router = APIRouter(prefix="/api/connections", tags=["connections"])


class ConnectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    dialect: str
    url: str = Field(min_length=1)


class ConnectionResponse(BaseModel):
    id: int
    name: str
    dialect: str
    read_only_status: str


class ReadonlySnippetResponse(BaseModel):
    dialect: str
    sql: str


class SamplesResponse(BaseModel):
    questions: list[str]


def _response(connection: DatabaseConnection) -> ConnectionResponse:
    return ConnectionResponse(
        id=connection.id,
        name=connection.name,
        dialect=connection.dialect,
        read_only_status=connection.read_only_status,
    )


@router.get("", response_model=list[ConnectionResponse])
def list_connections(
    _user: User = Depends(current_user),
    database: Session = Depends(get_db),
) -> list[ConnectionResponse]:
    connections = database.scalars(select(DatabaseConnection).order_by(DatabaseConnection.name))
    return [_response(connection) for connection in connections]


@router.post("", response_model=ConnectionResponse, status_code=201)
def create_connection(
    payload: ConnectionCreate,
    _admin: User = Depends(require_role("admin")),
    database: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ConnectionResponse:
    if database.scalar(
        select(DatabaseConnection).where(DatabaseConnection.name == payload.name.strip())
    ):
        raise HTTPException(status_code=409, detail="Connection name already exists")
    try:
        connector = SQLAlchemyConnector(payload.url)
    except (ValueError, ImportError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if connector.dialect != payload.dialect:
        raise HTTPException(status_code=422, detail="URL does not match selected dialect")
    if not connector.test_connection():
        raise HTTPException(status_code=400, detail="Could not connect to database")

    read_only = connector.is_read_only()
    connection = DatabaseConnection(
        name=payload.name.strip(),
        dialect=connector.dialect,
        encrypted_url=encrypt_value(payload.url, settings.app_secret),
        read_only_status=(
            "verified" if read_only is True else "writable" if read_only is False else "unknown"
        ),
    )
    database.add(connection)
    database.commit()
    database.refresh(connection)
    return _response(connection)


@router.get("/{connection_id}/samples", response_model=SamplesResponse)
def sample_questions(
    connection_id: int,
    _user: User = Depends(current_user),
    database: Session = Depends(get_db),
) -> SamplesResponse:
    connection = database.get(DatabaseConnection, connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")
    path = Path(__file__).parents[2] / "sample_data" / "questions.json"
    return SamplesResponse(questions=json.loads(path.read_text()))


@router.get("/{connection_id}/readonly-snippet", response_model=ReadonlySnippetResponse)
def readonly_snippet(
    connection_id: int,
    _admin: User = Depends(require_role("admin")),
    database: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ReadonlySnippetResponse:
    connection = database.get(DatabaseConnection, connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")
    dialect = connector_from_record(connection, settings).dialect
    snippets = {
        "postgres": (
            "CREATE ROLE text2sql_reader LOGIN PASSWORD 'change-me';\n"
            "GRANT CONNECT ON DATABASE your_database TO text2sql_reader;\n"
            "GRANT USAGE ON SCHEMA public TO text2sql_reader;\n"
            "GRANT SELECT ON ALL TABLES IN SCHEMA public TO text2sql_reader;"
        ),
        "mysql": (
            "CREATE USER 'text2sql_reader'@'%' IDENTIFIED BY 'change-me';\n"
            "GRANT SELECT ON your_database.* TO 'text2sql_reader'@'%';"
        ),
        "sqlite": "-- SQLite files do not have database roles.",
    }
    return ReadonlySnippetResponse(dialect=dialect, sql=snippets[dialect])
