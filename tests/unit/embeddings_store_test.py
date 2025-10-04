import pytest
from sqlalchemy.orm import Session

from app.core import config
from app.db.engine import get_engine, get_session_factory
from app.db.models import Base
from app.embeddings.openai_embed import OpenAIEmbeddingProvider
from app.embeddings.store import EmbeddingStore
from app.db.models import EmbeddingIndexModel


@pytest.fixture()
def db_session(tmp_path, monkeypatch) -> Session:
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    db_path = tmp_path / "embeddings.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    config.get_settings.cache_clear()
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        config.get_settings.cache_clear()


def test_embedding_store_similarity(db_session):
    provider = OpenAIEmbeddingProvider()
    store = EmbeddingStore(db_session, provider)
    store.add_document("doc", "standards", "Coding standards and lint rules")
    store.add_document("doc", "operations", "Deployment checklist and runbooks")
    db_session.commit()
    results = store.similarity_search("doc", "lint rules", limit=1)
    assert results
    ref_id, score, _ = results[0]
    doc_ids = {row.ref_id for row in db_session.query(EmbeddingIndexModel.ref_id).all()}
    assert ref_id in doc_ids
    assert 0 <= score <= 1
