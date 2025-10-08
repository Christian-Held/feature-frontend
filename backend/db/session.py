"""SQLAlchemy engine and session management."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.core.config import get_settings
from backend.db.base import Base


def _create_engine():
    settings = get_settings()
    # Handle both string and PostgresDsn types
    db_url = settings.database_url
    if hasattr(db_url, 'unicode_string'):
        db_url = db_url.unicode_string()
    return create_engine(str(db_url), echo=settings.database_echo, pool_pre_ping=True, future=True)


engine = _create_engine()

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False, class_=Session)


def init_db() -> None:
    """Initialize database metadata (used primarily for tests)."""

    Base.metadata.create_all(bind=engine)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""

    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Iterator[Session]:
    """FastAPI dependency that yields a database session."""

    with session_scope() as session:
        yield session


__all__ = ["engine", "SessionLocal", "session_scope", "get_db", "init_db"]

