from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, List, Sequence

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class RankedCandidate:
    id: str
    source: str
    content: str
    score: float
    tokens: int
    metadata: dict


def _tokenize(text: str) -> List[str]:
    return [token.lower() for token in text.split() if token.strip()]


def _bm25_light(query_tokens: Sequence[str], doc_tokens: Sequence[str]) -> float:
    if not doc_tokens or not query_tokens:
        return 0.0
    query_counts = Counter(query_tokens)
    doc_counts = Counter(doc_tokens)
    score = 0.0
    avg_doc_len = max(1, len(doc_tokens))
    for term, q_count in query_counts.items():
        d_tf = doc_counts.get(term, 0)
        if d_tf == 0:
            continue
        numerator = (1.2 + 1) * d_tf
        denominator = d_tf + 1.2 * (0.25 + 0.75 * (len(doc_tokens) / avg_doc_len))
        score += q_count * (numerator / denominator)
    return score


def _cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class Curator:
    def __init__(self, embedding_provider):
        self.embedding_provider = embedding_provider
        settings = get_settings()
        self.top_k = settings.curator_topk
        self.min_score = settings.curator_min_score

    def rank(self, query: str, candidates: Iterable[dict]) -> List[RankedCandidate]:
        query_tokens = _tokenize(query)
        query_vec = self.embedding_provider.embed_texts([query])[0]
        docs = list(candidates)
        if not docs:
            return []
        doc_vecs = self.embedding_provider.embed_texts([doc["content"] for doc in docs])
        ranked: List[RankedCandidate] = []
        for doc, vec in zip(docs, doc_vecs):
            doc_tokens = _tokenize(doc["content"])
            bm25_score = _bm25_light(query_tokens, doc_tokens)
            cosine = _cosine_similarity(query_vec, vec)
            score = 0.6 * bm25_score + 0.4 * cosine
            if score < self.min_score:
                continue
            ranked.append(
                RankedCandidate(
                    id=doc["id"],
                    source=doc.get("source", "unknown"),
                    content=doc["content"],
                    score=score,
                    tokens=doc.get("tokens", 0),
                    metadata=doc.get("metadata", {}),
                )
            )
        ranked.sort(key=lambda c: c.score, reverse=True)
        final = ranked[: self.top_k]
        logger.info(
            "curator_ranked",
            query_tokens=len(query_tokens),
            candidates=len(docs),
            selected=len(final),
        )
        return final
