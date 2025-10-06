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
    return create_engine(settings.database_url.unicode_string(), echo=settings.database_echo, pool_pre_ping=True, future=True)


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

