from types import SimpleNamespace

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.main import app


def test_health() -> None:
    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "version": "0.1.0"}


def test_llm_status(monkeypatch: MonkeyPatch) -> None:
    async def reachable(_self: object) -> bool:
        return True

    client = SimpleNamespace(model="qwen2.5-coder:7b", is_reachable=reachable)
    client.is_reachable = lambda: reachable(client)
    monkeypatch.setattr(
        "app.api.llm.resolve_llm",
        lambda _database, _settings: SimpleNamespace(provider="ollama", client=client),
    )
    response = TestClient(app).get("/api/llm/status")

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "ollama"
    assert body["model"] == "qwen2.5-coder:7b"
    assert body["reachable"] is True
    assert isinstance(body["latency_ms"], int)
