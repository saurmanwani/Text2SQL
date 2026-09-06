from typing import Any

import pytest

from app.connectors.base import ColumnModel, SchemaModel, TableModel
from app.db.models import SchemaPermission
from app.knowledge.visibility import filter_schema
from app.pipeline.nodes.summarize import summarize
from app.safety.redact import redact_rows


def test_hidden_table_and_column_are_removed_from_schema() -> None:
    schema = SchemaModel(
        tables=[
            TableModel(
                name="payroll",
                columns=[ColumnModel(name="salary", type="INTEGER", nullable=False)],
            ),
            TableModel(
                name="employees",
                columns=[
                    ColumnModel(name="name", type="TEXT", nullable=False),
                    ColumnModel(name="email", type="TEXT", nullable=False),
                ],
            ),
        ]
    )
    permissions = [
        SchemaPermission(role="analyst", table_name="payroll", column_name=None, visible=False),
        SchemaPermission(
            role="analyst",
            table_name="employees",
            column_name="email",
            visible=False,
        ),
    ]

    visible = filter_schema(schema, "analyst", permissions)

    assert [table.name for table in visible.tables] == ["employees"]
    assert [column.name for column in visible.tables[0].columns] == ["name"]


def test_redacts_pii_in_rows() -> None:
    rows = [["me@example.com", "+1 (415) 555-0100", "123456789012", 42]]

    assert redact_rows(rows) == [
        ["[REDACTED_EMAIL]", "[REDACTED_PHONE]", "[REDACTED_NUMBER]", 42]
    ]


@pytest.mark.asyncio
async def test_cloud_summary_prompt_receives_redacted_rows() -> None:
    class CapturingLLM:
        prompt = ""

        async def chat(self, messages: list[dict[str, Any]]) -> str:
            self.prompt = str(messages[0]["content"])
            return "Summary"

    llm = CapturingLLM()
    result = await summarize(
        {
            "question": "Who?",
            "llm": llm,
            "columns": ["email"],
            "rows": [["person@example.com"]],
            "summaries_enabled": True,
            "redact_before_summary": True,
        }
    )

    assert result["summary"] == "Summary"
    assert "[REDACTED_EMAIL]" in llm.prompt
    assert "person@example.com" not in llm.prompt
