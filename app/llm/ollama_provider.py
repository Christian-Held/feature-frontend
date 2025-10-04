from __future__ import annotations

from typing import Any, Dict, List

import httpx

from app.core.logging import get_logger

from .provider import BaseLLMProvider, LLMResponse, estimate_tokens

logger = get_logger(__name__)


class OllamaLLMProvider(BaseLLMProvider):
    name = "ollama"

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip("/")

    async def generate(self, *, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> LLMResponse:
        prompt = "\n".join(msg.get("content", "") for msg in messages)
        payload = {"model": model, "prompt": prompt}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(f"{self.base_url}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
        text = data.get("response", "")
        tokens_in = estimate_tokens(prompt)
        tokens_out = estimate_tokens(text)
        logger.info("ollama_call", model=model, tokens_in=tokens_in, tokens_out=tokens_out)
        return LLMResponse(text=text, tokens_in=tokens_in, tokens_out=tokens_out)
