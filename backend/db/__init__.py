"""Database convenience exports with lazy session imports."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

from backend.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:  # pragma: no cover - for static type checking only
    from backend.db.session import SessionLocal, engine, get_db, init_db, session_scope  # noqa: F401


def __getattr__(name: str) -> Any:
    if name in {"SessionLocal", "engine", "get_db", "init_db", "session_scope"}:
        module = import_module("backend.db.session")
        return getattr(module, name)
    raise AttributeError(name)


__all__ = [
    "Base",
    "TimestampMixin",
    "UUIDPrimaryKeyMixin",
    "SessionLocal",
    "engine",
    "get_db",
    "init_db",
    "session_scope",
]
