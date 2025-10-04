from __future__ import annotations

import json
from typing import List, Tuple

from sqlalchemy.orm import Session

from app.db.models import EmbeddingIndexModel

from .provider import BaseEmbeddingProvider, cosine_similarity


class EmbeddingStore:
    def __init__(self, session: Session, provider: BaseEmbeddingProvider):
        self.session = session
        self.provider = provider

    def add_document(self, scope: str, ref_id: str, text: str) -> EmbeddingIndexModel:
        vector = self.provider.embed_texts([text])[0]
        existing = (
            self.session.query(EmbeddingIndexModel)
            .filter(EmbeddingIndexModel.scope == scope, EmbeddingIndexModel.ref_id == ref_id)
            .first()
        )
        payload = json.dumps(vector)
        if existing:
            existing.text = text
            existing.vector = payload
            self.session.add(existing)
            self.session.flush()
            return existing
        model = EmbeddingIndexModel(scope=scope, ref_id=ref_id, text=text, vector=payload)
        self.session.add(model)
        self.session.flush()
        return model

    def similarity_search(self, scope: str, query: str, limit: int = 5) -> List[Tuple[str, float, str]]:
        query_vec = self.provider.embed_texts([query])[0]
        records = (
            self.session.query(EmbeddingIndexModel)
            .filter(EmbeddingIndexModel.scope == scope)
            .all()
        )
        scored: List[Tuple[str, float, str]] = []
        for record in records:
            vector = json.loads(record.vector)
            score = cosine_similarity(query_vec, vector)
            scored.append((record.ref_id, score, record.text))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:limit]
