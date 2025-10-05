from __future__ import annotations

from typing import List

from sqlalchemy.orm import Session

from app.embeddings.store import EmbeddingStore


def collect_external_docs(session: Session, provider, query: str, limit: int = 5) -> List[dict]:
    store = EmbeddingStore(session, provider)
    results = store.similarity_search("doc", query, limit=limit)
    payload: List[dict] = []
    for ref_id, score, text in results:
        payload.append(
            {
                "id": f"doc::{ref_id}",
                "source": "doc",
                "content": text,
                "tokens": provider.count_tokens(text),
                "metadata": {"score": score, "ref_id": ref_id},
            }
        )
    return payload
