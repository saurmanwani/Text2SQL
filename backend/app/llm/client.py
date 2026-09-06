import asyncio
from collections.abc import Mapping, Sequence
from typing import Any

import httpx


class LLMResponseError(RuntimeError):
    """Raised when an LLM response does not contain assistant text."""


class LLMClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self._transport = transport
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            return {}
        return {"Authorization": f"Bearer {self.api_key}"}

    async def chat(
        self,
        messages: Sequence[Mapping[str, Any]],
        temperature: float = 0,
        json_mode: bool = False,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [dict(message) for message in messages],
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._headers(),
            timeout=self._timeout,
            transport=self._transport,
        ) as client:
            response = await self._post_with_retries(client, payload)

        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMResponseError("LLM response did not contain assistant text") from exc
        if not isinstance(content, str):
            raise LLMResponseError("LLM response content was not text")
        return content

    async def _post_with_retries(
        self, client: httpx.AsyncClient, payload: dict[str, Any]
    ) -> httpx.Response:
        for attempt in range(3):
            try:
                response = await client.post("/chat/completions", json=payload)
                if response.status_code < 500:
                    response.raise_for_status()
                    return response
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt == 2:
                    raise
            else:
                if attempt == 2:
                    response.raise_for_status()

            await asyncio.sleep(0.25 * (2**attempt))

        raise RuntimeError("LLM request retry loop exited unexpectedly")

    async def is_reachable(self) -> bool:
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                headers=self._headers(),
                timeout=min(self._timeout, 5.0),
                transport=self._transport,
            ) as client:
                response = await client.get("/models")
            return response.is_success
        except httpx.RequestError:
            return False
