import json
from unittest.mock import AsyncMock

import httpx
import pytest

from app.llm.client import LLMClient


@pytest.mark.asyncio
async def test_chat_retries_5xx_and_sends_json_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) < 3:
            return httpx.Response(503, request=request)
        return httpx.Response(
            200,
            request=request,
            json={"choices": [{"message": {"content": '{"sql":"SELECT 1"}'}}]},
        )

    sleep = AsyncMock()
    monkeypatch.setattr("app.llm.client.asyncio.sleep", sleep)
    client = LLMClient(
        "http://llm.test/v1/",
        "secret",
        "test-model",
        transport=httpx.MockTransport(handler),
    )

    result = await client.chat(
        [{"role": "user", "content": "Return SQL"}],
        json_mode=True,
    )

    assert result == '{"sql":"SELECT 1"}'
    assert len(requests) == 3
    assert sleep.await_count == 2
    assert requests[-1].headers["authorization"] == "Bearer secret"
    payload = json.loads(requests[-1].content)
    assert payload["temperature"] == 0
    assert payload["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_chat_retries_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ReadTimeout("timed out", request=request)
        return httpx.Response(
            200,
            request=request,
            json={"choices": [{"message": {"content": "SELECT 1"}}]},
        )

    monkeypatch.setattr("app.llm.client.asyncio.sleep", AsyncMock())
    client = LLMClient(
        "http://llm.test/v1",
        "",
        "test-model",
        transport=httpx.MockTransport(handler),
    )

    assert await client.chat([{"role": "user", "content": "SQL"}]) == "SELECT 1"
    assert attempts == 2
