from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, List, Sequence


class BaseEmbeddingProvider(ABC):
    model: str

    @abstractmethod
    def embed_texts(self, texts: Sequence[str]) -> List[List[float]]:
        """Return embeddings for each text."""

    def count_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)


def cosine_similarity(vec_a: Iterable[float], vec_b: Iterable[float]) -> float:
    sum_aa = 0.0
    sum_bb = 0.0
    sum_ab = 0.0
    for a, b in zip(vec_a, vec_b):
        sum_ab += a * b
        sum_aa += a * a
        sum_bb += b * b
    if sum_aa == 0 or sum_bb == 0:
        return 0.0
    return sum_ab / ((sum_aa ** 0.5) * (sum_bb ** 0.5))
