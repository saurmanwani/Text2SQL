import sqlite3
from collections.abc import Generator
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import current_user
from app.core.crypto import encrypt_value
from app.db.models import AuditEvent, Base, DatabaseConnection, User, VerifiedExample
from app.db.session import get_db
from app.main import app
from app.settings import get_settings


class FakeStore:
    saved: VerifiedExample | None = None

    def upsert_example(self, example: VerifiedExample) -> None:
        self.saved = example


def test_correction_is_validated_executed_and_saved(
    tmp_path: Path,
    monkeypatch,
) -> None:
    target_path = tmp_path / "feedback.db"
    target = sqlite3.connect(target_path)
    target.executescript(
        "CREATE TABLE sales (amount INTEGER); INSERT INTO sales VALUES (10), (20);"
    )
    target.commit()
    target.close()

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    settings = get_settings()
    with session_factory() as database:
        user = User(email="analyst@example.com", password_hash="unused", role="analyst")
        connection = DatabaseConnection(
            name="Test",
            dialect="sqlite",
            encrypted_url=encrypt_value(f"sqlite:///{target_path}", settings.app_secret),
            read_only_status="unknown",
        )
        database.add_all([user, connection])
        database.flush()
        audit = AuditEvent(
            user_id=user.id,
            connection_id=connection.id,
            question="What is total sales?",
            sql="SELECT amount FROM sales",
            tables_touched=["sales"],
            row_count=2,
            duration_ms=1,
            provider="ollama",
            model="test",
            attempts=1,
            outcome="ok",
            summary_sent_to_cloud=False,
        )
        database.add(audit)
        database.commit()
        user_id, audit_id = user.id, audit.id

    def override_database() -> Generator[Session, None, None]:
        with session_factory() as database:
            yield database

    def override_user() -> User:
        with session_factory() as database:
            user = database.get(User, user_id)
            assert user is not None
            return user

    store = FakeStore()
    app.dependency_overrides[get_db] = override_database
    app.dependency_overrides[current_user] = override_user
    monkeypatch.setattr("app.api.feedback.get_knowledge_store", lambda: store)
    try:
        response = TestClient(app).post(
            "/api/feedback",
            json={
                "audit_event_id": audit_id,
                "verdict": "down",
                "issue": "wrong_aggregation",
                "corrected_sql": "SELECT SUM(amount) AS total FROM sales",
            },
        )
        assert response.status_code == 200
        assert response.json()["rows"] == [[30]]
        with session_factory() as database:
            example = database.scalar(select(VerifiedExample))
            assert example is not None
            assert "SUM(amount)" in example.sql
        assert store.saved is not None
    finally:
        app.dependency_overrides.clear()
