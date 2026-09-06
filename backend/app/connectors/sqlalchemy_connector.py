from time import monotonic
from typing import Any

from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.engine import URL, Connection, make_url

from app.connectors.base import ColumnModel, Connector, QueryResult, SchemaModel, TableModel

SQLGLOT_DIALECTS = {
    "postgresql": "postgres",
    "mysql": "mysql",
    "sqlite": "sqlite",
}


class SQLAlchemyConnector(Connector):
    def __init__(
        self,
        url: str | URL,
        *,
        statement_timeout_ms: int = 30_000,
    ) -> None:
        self.url = make_url(url)
        try:
            self.dialect = SQLGLOT_DIALECTS[self.url.get_backend_name()]
        except KeyError as exc:
            backend = self.url.get_backend_name()
            raise ValueError(f"Unsupported database dialect: {backend}") from exc
        self.statement_timeout_ms = statement_timeout_ms
        self.engine: Engine = create_engine(self.url, pool_pre_ping=True)

    def test_connection(self) -> bool:
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def get_schema(self) -> SchemaModel:
        inspector = inspect(self.engine)
        tables: list[TableModel] = []
        for table_name in sorted(inspector.get_table_names()):
            primary_keys = set(
                inspector.get_pk_constraint(table_name).get("constrained_columns") or []
            )
            foreign_keys: dict[str, list[str]] = {}
            for foreign_key in inspector.get_foreign_keys(table_name):
                referred_table = foreign_key.get("referred_table")
                constrained = foreign_key.get("constrained_columns") or []
                referred = foreign_key.get("referred_columns") or []
                if not referred_table:
                    continue
                for source, target in zip(constrained, referred, strict=False):
                    foreign_keys.setdefault(source, []).append(f"{referred_table}.{target}")

            columns = [
                ColumnModel(
                    name=column["name"],
                    type=str(column["type"]),
                    nullable=bool(column.get("nullable", True)),
                    primary_key=column["name"] in primary_keys,
                    foreign_key_targets=foreign_keys.get(column["name"], []),
                )
                for column in inspector.get_columns(table_name)
            ]
            tables.append(TableModel(name=table_name, columns=columns))
        return SchemaModel(tables=tables)

    def execute(self, sql: str, row_limit: int) -> QueryResult:
        if row_limit < 1:
            raise ValueError("row_limit must be positive")

        with self.engine.connect() as connection:
            transaction = connection.begin()
            sqlite_connection: Any | None = None
            try:
                if self.dialect == "postgres":
                    connection.execute(
                        text(f"SET LOCAL statement_timeout = {self.statement_timeout_ms}")
                    )
                elif self.dialect == "sqlite":
                    sqlite_connection = connection.connection.driver_connection
                    deadline = monotonic() + (self.statement_timeout_ms / 1000)
                    sqlite_connection.set_progress_handler(
                        lambda: int(monotonic() >= deadline),
                        1_000,
                    )

                result = connection.execute(text(self._limited_sql(sql, row_limit)))
                columns = list(result.keys())
                rows = [list(row) for row in result.fetchall()]
                return QueryResult(columns=columns, rows=rows, row_count=len(rows))
            finally:
                if sqlite_connection is not None:
                    sqlite_connection.set_progress_handler(None, 0)
                transaction.rollback()

    def _limited_sql(self, sql: str, row_limit: int) -> str:
        clean_sql = sql.strip().removesuffix(";")
        if self.dialect == "mysql":
            return (
                f"SELECT /*+ MAX_EXECUTION_TIME({self.statement_timeout_ms}) */ * "
                f"FROM ({clean_sql}) AS _text2sql_query LIMIT {row_limit}"
            )
        return f"SELECT * FROM ({clean_sql}) AS _text2sql_query LIMIT {row_limit}"

    def is_read_only(self) -> bool | None:
        if self.dialect == "sqlite":
            return None
        with self.engine.connect() as connection:
            if self.dialect == "postgres":
                return self._postgres_is_read_only(connection)
            return self._mysql_is_read_only(connection)

    @staticmethod
    def _postgres_is_read_only(connection: Connection) -> bool:
        elevated = connection.execute(
            text(
                "SELECT rolsuper OR rolcreatedb "
                "FROM pg_roles WHERE rolname = current_user"
            )
        ).scalar_one()
        if elevated:
            return False
        writable = connection.execute(
            text(
                "SELECT EXISTS ("
                "SELECT 1 FROM pg_tables "
                "WHERE schemaname NOT IN ('pg_catalog', 'information_schema') "
                "AND (has_table_privilege("
                "quote_ident(schemaname) || '.' || quote_ident(tablename), 'INSERT') "
                "OR has_table_privilege("
                "quote_ident(schemaname) || '.' || quote_ident(tablename), 'UPDATE') "
                "OR has_table_privilege("
                "quote_ident(schemaname) || '.' || quote_ident(tablename), 'DELETE'))"
                ")"
            )
        ).scalar_one()
        return not bool(writable)

    @staticmethod
    def _mysql_is_read_only(connection: Connection) -> bool:
        write_privileges = {
            "ALL",
            "ALTER",
            "CREATE",
            "DELETE",
            "DROP",
            "INSERT",
            "UPDATE",
        }
        for row in connection.execute(text("SHOW GRANTS")):
            grant = str(row[0]).upper()
            privileges = grant.partition(" ON ")[0].removeprefix("GRANT ")
            granted = {item.strip().split()[0] for item in privileges.split(",")}
            if granted & write_privileges:
                return False
        return True
