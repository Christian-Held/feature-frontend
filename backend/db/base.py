"""Database base classes and mixins for SQLAlchemy models."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

from backend.db.types import GUID


class Base(DeclarativeBase):
    """Declarative base class providing naming conventions."""

    @declared_attr.directive
    def __tablename__(cls) -> str:  # type: ignore[misc]
        return cls.__name__.lower()


class UUIDPrimaryKeyMixin:
    """Mixin providing a UUID primary key column."""

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)


def _utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp for defaults."""

    return datetime.now(timezone.utc)


class TimestampMixin:
    """Mixin adding created and updated timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
        server_default=func.now(),
    )


__all__ = ["Base", "TimestampMixin", "UUIDPrimaryKeyMixin"]

