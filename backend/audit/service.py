"""Audit logging service for tracking sensitive operations."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.orm import Session

from backend.db.models.audit_event import AuditEvent

logger = structlog.get_logger(__name__)


def create_audit_event(
    db: Session,
    action: str,
    actor_id: UUID | None = None,
    resource_type: str | None = None,
    resource_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditEvent:
    """
    Create an audit log entry.

    Args:
        db: Database session
        action: Action performed (e.g., 'user.created', 'subscription.upgraded')
        actor_id: ID of user who performed the action
        resource_type: Type of resource affected (e.g., 'user', 'subscription')
        resource_id: ID of affected resource
        metadata: Additional context data
        ip_address: IP address of the request
        user_agent: User agent string of the request

    Returns:
        Created AuditEvent instance
    """
    event = AuditEvent(
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata=metadata or {},
        ip_address=ip_address,
        user_agent=user_agent,
        created_at=datetime.utcnow(),
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    logger.info(
        "audit.event.created",
        action=action,
        actor_id=str(actor_id) if actor_id else None,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else None,
    )

    return event


def get_audit_events(
    db: Session,
    actor_id: UUID | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[AuditEvent]:
    """
    Query audit events with filters.

    Args:
        db: Database session
        actor_id: Filter by actor
        action: Filter by action
        resource_type: Filter by resource type
        resource_id: Filter by resource ID
        limit: Maximum number of events to return
        offset: Number of events to skip

    Returns:
        List of matching AuditEvent instances
    """
    query = db.query(AuditEvent)

    if actor_id:
        query = query.filter(AuditEvent.actor_id == actor_id)

    if action:
        query = query.filter(AuditEvent.action == action)

    if resource_type:
        query = query.filter(AuditEvent.resource_type == resource_type)

    if resource_id:
        query = query.filter(AuditEvent.resource_id == resource_id)

    # Order by most recent first
    query = query.order_by(AuditEvent.created_at.desc())

    return query.offset(offset).limit(limit).all()


def get_audit_events_count(
    db: Session,
    actor_id: UUID | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: UUID | None = None,
) -> int:
    """Get count of audit events matching filters."""
    query = db.query(AuditEvent)

    if actor_id:
        query = query.filter(AuditEvent.actor_id == actor_id)

    if action:
        query = query.filter(AuditEvent.action == action)

    if resource_type:
        query = query.filter(AuditEvent.resource_type == resource_type)

    if resource_id:
        query = query.filter(AuditEvent.resource_id == resource_id)

    return query.count()


def log_user_action(
    db: Session,
    actor_id: UUID,
    action: str,
    target_user_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditEvent:
    """
    Helper function to log user-related actions.

    Args:
        db: Database session
        actor_id: ID of user performing the action
        action: Action performed
        target_user_id: ID of affected user (if different from actor)
        metadata: Additional context
        ip_address: IP address
        user_agent: User agent

    Returns:
        Created AuditEvent instance
    """
    return create_audit_event(
        db=db,
        action=action,
        actor_id=actor_id,
        resource_type="user",
        resource_id=target_user_id or actor_id,
        metadata=metadata,
        ip_address=ip_address,
        user_agent=user_agent,
    )


def log_subscription_action(
    db: Session,
    actor_id: UUID,
    action: str,
    subscription_id: UUID,
    metadata: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditEvent:
    """Helper function to log subscription-related actions."""
    return create_audit_event(
        db=db,
        action=action,
        actor_id=actor_id,
        resource_type="subscription",
        resource_id=subscription_id,
        metadata=metadata,
        ip_address=ip_address,
        user_agent=user_agent,
    )


def log_admin_action(
    db: Session,
    admin_id: UUID,
    action: str,
    resource_type: str | None = None,
    resource_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditEvent:
    """Helper function to log admin actions."""
    return create_audit_event(
        db=db,
        action=action,
        actor_id=admin_id,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata=metadata,
        ip_address=ip_address,
        user_agent=user_agent,
    )
