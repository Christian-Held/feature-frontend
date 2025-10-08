"""Audit event model for tracking sensitive operations."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, relationship

from backend.db.base import Base

if TYPE_CHECKING:
    from backend.db.models.user import User


class AuditEvent(Base):
    """Audit log for tracking sensitive operations and admin actions."""

    __tablename__ = "audit_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Who performed the action
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # What action was performed
    action = Column(String(100), nullable=False, index=True)
    # Examples: 'user.created', 'user.suspended', 'user.deleted',
    #           'subscription.upgraded', 'subscription.cancelled',
    #           'admin.login', 'rate_limit.cleared', 'session.revoked'

    # What resource was affected
    resource_type = Column(String(50), nullable=True, index=True)
    # Examples: 'user', 'subscription', 'session', 'api_key'
    resource_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Additional context
    event_metadata = Column("event_metadata", JSONB, nullable=True)
    # Store action-specific data: {'old_plan': 'free', 'new_plan': 'pro'}

    # Request context
    ip_address = Column(String(45), nullable=True)  # IPv6 max length
    user_agent = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    actor: Mapped["User"] = relationship("User", foreign_keys=[actor_id], back_populates="audit_events")

    __table_args__ = (
        Index("idx_audit_events_actor_id", "actor_id"),
        Index("idx_audit_events_action", "action"),
        Index("idx_audit_events_resource", "resource_type", "resource_id"),
        Index("idx_audit_events_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AuditEvent(action='{self.action}', actor_id='{self.actor_id}', resource='{self.resource_type}:{self.resource_id}')>"
