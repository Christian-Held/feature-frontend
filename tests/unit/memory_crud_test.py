import os

import pytest
from sqlalchemy.orm import Session

from app.context.memory_store import MemoryLimitError, MemoryStore
from app.core import config
from app.db.engine import get_engine, get_session_factory
from app.db.models import Base


@pytest.fixture()
def db_session(tmp_path, monkeypatch) -> Session:
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    db_path = tmp_path / "memory.db"
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


def test_memory_store_add_and_list(db_session):
    store = MemoryStore()
    note = store.add_note(
        db_session,
        "job-1",
        {"type": "Decision", "title": "Pick DB", "body": "Use SQLite", "tags": ["db"]},
    )
    db_session.commit()
    assert note["title"] == "Pick DB"
    memory = store.get_memory(db_session, "job-1")
    assert memory["notes"]
    path, size = store.add_file(db_session, "job-1", "design.md", b"# Design")
    db_session.commit()
    assert size == len(b"# Design")
    assert store.get_memory(db_session, "job-1")["files"]


def test_memory_store_enforces_limits(db_session, monkeypatch):
    monkeypatch.setenv("MEMORY_MAX_ITEMS_PER_JOB", "1")
    config.get_settings.cache_clear()
    store = MemoryStore()
    store.add_note(db_session, "job-2", {"type": "Decision", "title": "A", "body": "B"})
    with pytest.raises(MemoryLimitError):
        store.add_note(db_session, "job-2", {"type": "Decision", "title": "C", "body": "D"})
