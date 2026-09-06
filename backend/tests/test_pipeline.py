import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from app.connectors.sqlalchemy_connector import SQLAlchemyConnector
from app.pipeline.graph import build_pipeline


class MockLLM:
    def __init__(self) -> None:
        self.generation_attempts = 0

    async def chat(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0,
        json_mode: bool = False,
    ) -> str:
        del temperature, json_mode
        prompt = str(messages[0]["content"])
        if "Suggest exactly three" in prompt:
            return json.dumps({"questions": ["By region?", "By month?", "By product?"]})
        if "Answer the question from these query results" in prompt:
            return "The total revenue is 30."
        self.generation_attempts += 1
        if self.generation_attempts == 1:
            return json.dumps({"sql": "DELETE FROM sales", "unanswerable": False})
        return json.dumps(
            {"sql": "SELECT SUM(revenue) AS total FROM sales", "unanswerable": False}
        )


@pytest.mark.asyncio
async def test_pipeline_retries_invalid_sql_then_executes(tmp_path: Path) -> None:
    path = tmp_path / "pipeline.db"
    database = sqlite3.connect(path)
    database.executescript(
        "CREATE TABLE sales (id INTEGER PRIMARY KEY, revenue REAL);"
        "INSERT INTO sales VALUES (1, 10), (2, 20);"
    )
    database.commit()
    database.close()
    connector = SQLAlchemyConnector(f"sqlite:///{path}")
    llm = MockLLM()

    state = await build_pipeline().ainvoke(
        {
            "question": "What is total revenue?",
            "connector": connector,
            "llm": llm,
            "role": "admin",
            "permissions": [],
            "attempt": 0,
            "max_attempts": 3,
            "max_rows": 100,
            "history": [],
            "summaries_enabled": True,
            "redact_before_summary": False,
        }
    )

    assert state["attempt"] == 2
    assert state["validation"].ok
    assert state["columns"] == ["total"]
    assert state["rows"] == [[30.0]]
    assert state["summary"] == "The total revenue is 30."
    assert len(state["followups"]) == 3
