from __future__ import annotations

from typing import Dict, List

import httpx
import pytest

from app.core.config import get_settings
from app.llm.openai_provider import OpenAILLMProvider


class DummyAsyncClient:
    def __init__(self, responses: Dict[str, httpx.Response], calls: List[str], base_url: str, timeout: int):
        self._responses = responses
        self._calls = calls
        self.base_url = base_url
        self.timeout = timeout

    async def __aenter__(self) -> "DummyAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - testing convenience
        return None

    async def post(self, endpoint: str, *, content: str, headers: Dict[str, str]) -> httpx.Response:
        request_url = f"{self.base_url}{endpoint}"
        self._calls.append(request_url)
        response = self._responses.get(request_url)
        if response is None:
            response = httpx.Response(
                500,
                request=httpx.Request("POST", request_url),
            )
        return response


@pytest.mark.asyncio
async def test_openai_provider_retries_with_default_base_url_on_404(monkeypatch, tmp_path):
    provider = OpenAILLMProvider()
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "orchestrator.db"))
    get_settings.cache_clear()
    settings = get_settings()
    original_base_url = settings.openai_base_url
    settings.openai_base_url = "https://bad.example.com/v1/"

    calls: List[str] = []
    bad_request = httpx.Response(
        404,
        request=httpx.Request("POST", "https://bad.example.com/v1/chat/completions"),
    )
    success_request = httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": "hello"}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 7},
        },
        request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
    )
    responses = {
        "https://bad.example.com/v1/chat/completions": bad_request,
        "https://api.openai.com/v1/chat/completions": success_request,
    }

    def _client_factory(base_url: str, timeout: int) -> DummyAsyncClient:
        return DummyAsyncClient(responses, calls, base_url, timeout)

    monkeypatch.setattr(httpx, "AsyncClient", _client_factory)

    try:
        result = await provider.generate(model="gpt-test", messages=[{"role": "user", "content": "Hi"}])
    finally:
        settings.openai_base_url = original_base_url
        get_settings.cache_clear()

    assert result.text == "hello"
    assert calls == [
        "https://bad.example.com/v1/chat/completions",
        "https://api.openai.com/v1/chat/completions",
    ]


@pytest.mark.asyncio
async def test_openai_provider_raises_for_404_from_default_base_url(monkeypatch, tmp_path):
    provider = OpenAILLMProvider()
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "orchestrator.db"))
    get_settings.cache_clear()
    settings = get_settings()
    original_base_url = settings.openai_base_url
    settings.openai_base_url = "https://api.openai.com/v1"

    calls: List[str] = []
    failing_response = httpx.Response(
        404,
        request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
    )
    responses = {
        "https://api.openai.com/v1/chat/completions": failing_response,
    }

    def _client_factory(base_url: str, timeout: int) -> DummyAsyncClient:
        return DummyAsyncClient(responses, calls, base_url, timeout)

    monkeypatch.setattr(httpx, "AsyncClient", _client_factory)

    try:
        with pytest.raises(httpx.HTTPStatusError):
            await provider.generate(model="gpt-test", messages=[{"role": "user", "content": "Hi"}])
    finally:
        settings.openai_base_url = original_base_url
        get_settings.cache_clear()

    assert calls == ["https://api.openai.com/v1/chat/completions"]
