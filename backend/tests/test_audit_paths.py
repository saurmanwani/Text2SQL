from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import current_user
from app.core.crypto import encrypt_value
from app.db.models import AuditEvent, Base, DatabaseConnection, User
from app.db.session import get_db
from app.main import app
from app.safety.validator import ValidationResult
from app.settings import get_settings


class FakeGraph:
    def __init__(self, outcome: str) -> None:
        self.outcome = outcome

    async def ainvoke(self, _state: object) -> dict[str, object]:
        if self.outcome == "error":
            raise RuntimeError("LLM unavailable")
        validation = ValidationResult(
            ok=self.outcome != "blocked",
            sql="SELECT 1" if self.outcome != "blocked" else None,
            tables=["sales"],
            reason="table_not_allowed" if self.outcome == "blocked" else None,
        )
        return {
            "sql": "SELECT 1",
            "validation": validation,
            "rows": [[1]] if self.outcome == "ok" else [],
            "columns": ["value"] if self.outcome == "ok" else [],
            "attempt": 1,
            "unanswerable": self.outcome in {"unanswerable", "blocked"},
            "unanswerable_reason": "Cannot answer" if self.outcome != "ok" else None,
            "followups": [],
            "summary": "One" if self.outcome == "ok" else None,
        }


@pytest.mark.parametrize("outcome", ["ok", "unanswerable", "blocked", "error"])
def test_each_query_path_writes_exactly_one_audit_event(
    outcome: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    settings = get_settings()
    with session_factory() as database:
        user = User(email="user@example.com", password_hash="unused", role="admin")
        connection = DatabaseConnection(
            name="Test",
            dialect="sqlite",
            encrypted_url=encrypt_value("sqlite:///:memory:", settings.app_secret),
            read_only_status="unknown",
        )
        database.add_all([user, connection])
        database.commit()
        user_id = user.id
        connection_id = connection.id

    def override_database() -> Generator[Session, None, None]:
        with session_factory() as database:
            yield database

    def override_user() -> User:
        with session_factory() as database:
            user = database.get(User, user_id)
            assert user is not None
            return user

    app.dependency_overrides[get_db] = override_database
    app.dependency_overrides[current_user] = override_user
    monkeypatch.setattr("app.api.query.build_pipeline", lambda: FakeGraph(outcome))
    try:
        response = TestClient(app).post(
            "/api/query",
            json={"question": "Test?", "connection_id": connection_id},
        )
        assert response.status_code == 200
        if outcome == "blocked":
            assert response.json()["sql"] is None
            assert response.json()["tables_touched"] == []
        with session_factory() as database:
            assert database.scalar(select(func.count(AuditEvent.id))) == 1
            event = database.scalar(select(AuditEvent))
            assert event and event.outcome == outcome
    finally:
        app.dependency_overrides.clear()
