from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class ColumnModel(BaseModel):
    name: str
    type: str
    nullable: bool
    primary_key: bool = False
    foreign_key_targets: list[str] = Field(default_factory=list)
    description: str = ""


class TableModel(BaseModel):
    name: str
    columns: list[ColumnModel]
    description: str = ""


class SchemaModel(BaseModel):
    tables: list[TableModel]


class QueryResult(BaseModel):
    columns: list[str]
    rows: list[list[Any]]
    row_count: int


class Connector(ABC):
    dialect: str

    @abstractmethod
    def test_connection(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_schema(self) -> SchemaModel:
        raise NotImplementedError

    @abstractmethod
    def execute(self, sql: str, row_limit: int) -> QueryResult:
        raise NotImplementedError

    @abstractmethod
    def is_read_only(self) -> bool | None:
        raise NotImplementedError
