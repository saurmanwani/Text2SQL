from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base
from app.db.session import get_db
from app.main import app


def test_first_user_is_admin_and_viewer_cannot_use_admin_routes() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_database() -> Generator[Session, None, None]:
        with session_factory() as database:
            yield database

    app.dependency_overrides[get_db] = override_database
    client = TestClient(app)
    try:
        admin = client.post(
            "/api/auth/register",
            json={"email": "admin@example.com", "password": "password123"},
        )
        viewer = client.post(
            "/api/auth/register",
            json={"email": "viewer@example.com", "password": "password123"},
        )

        assert admin.status_code == 201
        assert admin.json()["user"]["role"] == "admin"
        assert viewer.json()["user"]["role"] == "viewer"

        response = client.get(
            "/api/admin/ai",
            headers={"Authorization": f"Bearer {viewer.json()['access_token']}"},
        )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()
