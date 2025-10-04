from __future__ import annotations

import hashlib
import json
from typing import List, Sequence

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

from .provider import BaseEmbeddingProvider

logger = get_logger(__name__)


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, model: str | None = None):
        settings = get_settings()
        self.model = model or settings.embedding_model
        self._settings = settings

    def _hash_embedding(self, text: str) -> List[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        # Produce a deterministic 32-dim vector
        vector = [int.from_bytes(digest[i : i + 2], "big") / 65535.0 for i in range(0, 64, 2)]
        return vector

    def embed_texts(self, texts: Sequence[str]) -> List[List[float]]:
        settings = self._settings
        if not settings.openai_api_key:
            return [self._hash_embedding(text) for text in texts]
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": self.model, "input": list(texts)}
        with httpx.Client(base_url=settings.openai_base_url, timeout=60) as client:
            response = client.post("/embeddings", content=json.dumps(payload), headers=headers)
            response.raise_for_status()
            data = response.json()
        vectors = [item["embedding"] for item in data.get("data", [])]
        if not vectors:
            logger.warning("openai_embedding_empty_response", count=len(texts))
            return [self._hash_embedding(text) for text in texts]
        return vectors
