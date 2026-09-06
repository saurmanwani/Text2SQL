from app.connectors.base import ColumnModel, Connector, QueryResult, SchemaModel, TableModel
from app.db.models import SchemaAnnotation
from app.pipeline.nodes.load_schema import load_schema
from app.pipeline.nodes.retrieve_examples import retrieve_examples


class SyntheticConnector(Connector):
    dialect = "sqlite"

    def test_connection(self) -> bool:
        return True

    def get_schema(self) -> SchemaModel:
        return SchemaModel(
            tables=[
                TableModel(
                    name=f"table_{index}",
                    columns=[
                        ColumnModel(name="id", type="INTEGER", nullable=False)
                    ],
                )
                for index in range(40)
            ]
        )

    def execute(self, sql: str, row_limit: int) -> QueryResult:
        del sql, row_limit
        return QueryResult(columns=[], rows=[], row_count=0)

    def is_read_only(self) -> bool | None:
        return True


class FakeStore:
    def query_tables(self, connection_id: int, question: str, limit: int) -> list[str]:
        del connection_id, question, limit
        return ["table_35", "table_2", "table_8", "table_9"]


def test_large_schema_retrieval_is_small_and_includes_annotation() -> None:
    result = load_schema(
        {
            "connector": SyntheticConnector(),
            "role": "admin",
            "permissions": [],
            "annotations": [
                SchemaAnnotation(
                    connection_id=1,
                    table_name="table_35",
                    column_name=None,
                    description="annual recurring revenue",
                )
            ],
            "knowledge_store": FakeStore(),
            "connection_id": 1,
            "question": "What is ARR?",
        }
    )

    tables = result["schema_tables"]
    assert isinstance(tables, list)
    assert len(tables) <= 10
    assert "table_35" in tables
    assert "annual recurring revenue" in str(result["schema_text"])


def test_retrieves_three_verified_examples_for_grounding() -> None:
    class ExampleStore:
        def query_examples(
            self, connection_id: int, question: str, limit: int
        ) -> list[dict[str, object]]:
            del connection_id, question, limit
            return [
                {"id": index, "question": f"Question {index}", "sql": "SELECT 1"}
                for index in range(1, 4)
            ]

    result = retrieve_examples(
        {
            "knowledge_store": ExampleStore(),
            "connection_id": 1,
            "question": "A paraphrase",
        }
    )

    assert result["grounded_on"] == [1, 2, 3]
