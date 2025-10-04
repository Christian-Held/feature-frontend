from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import deps
from app.core.logging import get_logger
from app.embeddings.openai_embed import OpenAIEmbeddingProvider
from app.embeddings.store import EmbeddingStore

router = APIRouter(prefix="/context", tags=["context"])
logger = get_logger(__name__)


class ContextDocRequest(BaseModel):
    title: str
    text: str


class ContextDocResponse(BaseModel):
    ref_id: str
    scope: str = "doc"


@router.post("/docs", response_model=ContextDocResponse, status_code=status.HTTP_201_CREATED)
def ingest_doc(payload: ContextDocRequest, session: Session = Depends(deps.get_db)) -> ContextDocResponse:
    if not payload.title.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Title is required")
    provider = OpenAIEmbeddingProvider()
    store = EmbeddingStore(session, provider)
    ref_id = payload.title.strip().lower().replace(" ", "-")
    store.add_document("doc", ref_id, f"{payload.title}\n\n{payload.text.strip()}")
    session.commit()
    logger.info("context_doc_ingested", ref_id=ref_id)
    return ContextDocResponse(ref_id=ref_id)
