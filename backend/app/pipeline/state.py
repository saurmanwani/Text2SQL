from typing import Any

from typing_extensions import TypedDict

from app.connectors.base import Connector
from app.db.models import SchemaAnnotation, SchemaPermission
from app.knowledge.store import KnowledgeStore
from app.llm.client import LLMClient
from app.safety.validator import ValidationResult


class HistoryTurn(TypedDict):
    question: str
    sql: str


class PipelineState(TypedDict, total=False):
    question: str
    dialect: str
    schema_text: str
    schema_tables: list[str]
    sql: str
    validation: ValidationResult
    attempt: int
    max_attempts: int
    rows: list[list[Any]]
    columns: list[str]
    summary: str | None
    summary_reason: str | None
    followups: list[str]
    error: str | None
    unanswerable: bool
    unanswerable_reason: str | None
    history: list[HistoryTurn]
    connector: Connector
    llm: LLMClient
    role: str
    permissions: list[SchemaPermission]
    max_rows: int
    summaries_enabled: bool
    redact_before_summary: bool
    connection_id: int
    annotations: list[SchemaAnnotation]
    knowledge_store: KnowledgeStore
    examples: list[dict[str, Any]]
    grounded_on: list[int]
