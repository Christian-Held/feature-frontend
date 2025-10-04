from __future__ import annotations

import json
from typing import Any, Dict, List

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

from .provider import BaseLLMProvider, LLMResponse, estimate_tokens

logger = get_logger(__name__)


class OpenAILLMProvider(BaseLLMProvider):
    name = "openai"

    async def generate(self, *, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> LLMResponse:
        settings = get_settings()
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": model, "messages": messages}
        payload.update(kwargs)
        async with httpx.AsyncClient(base_url=settings.openai_base_url, timeout=60) as client:
            response = await client.post("/chat/completions", content=json.dumps(payload), headers=headers)
            response.raise_for_status()
            data = response.json()
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        tokens_in = usage.get("prompt_tokens", estimate_tokens(json.dumps(messages)))
        tokens_out = usage.get("completion_tokens", estimate_tokens(text))
        logger.info("openai_call", model=model, tokens_in=tokens_in, tokens_out=tokens_out)
        return LLMResponse(text=text, tokens_in=tokens_in, tokens_out=tokens_out)

    def count_tokens(self, messages: List[Dict[str, str]]) -> int:
        payload = json.dumps(messages)
        return estimate_tokens(payload)
