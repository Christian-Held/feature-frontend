from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple


class LLMResponse:
    def __init__(self, text: str, tokens_in: int = 0, tokens_out: int = 0):
        self.text = text
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out


class BaseLLMProvider(ABC):
    name: str

    @abstractmethod
    async def generate(self, *, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> LLMResponse:
        ...


def estimate_tokens(text: str) -> int:
    # Cheap heuristic: 1 token ≈ 4 chars
    return max(1, len(text) // 4)


class DryRunLLMProvider(BaseLLMProvider):
    name = "dry-run"

    async def generate(self, *, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> LLMResponse:
        combined = "\n".join(msg.get("content", "") for msg in messages)
        response = f"DRY-RUN ({model}) RESPONSE: {combined[:200]}"
        tokens = estimate_tokens(combined)
        return LLMResponse(text=response, tokens_in=tokens, tokens_out=tokens // 2)
