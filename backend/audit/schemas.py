"""Pydantic schemas for audit API."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuditEventSchema(BaseModel):
    """Audit event schema."""

    id: UUID
    actor_id: UUID | None
    action: str
    resource_type: str | None
    resource_id: UUID | None
    metadata: dict[str, Any] | None = Field(default=None, alias="event_metadata")
    ip_address: str | None
    user_agent: str | None
    created_at: datetime

    # Include actor email for display
    actor_email: str | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AuditEventListResponse(BaseModel):
    """Response for audit event list."""

    events: list[AuditEventSchema]
    total: int
    limit: int
    offset: int


__all__ = [
    "AuditEventSchema",
    "AuditEventListResponse",
]
