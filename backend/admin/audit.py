"""Audit logging helpers for admin actions."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import UUID

import structlog
from sqlalchemy.orm import Session

from backend.db.models.audit import AuditLog

logger = structlog.get_logger(__name__)

AUDIT_TARGET_USER = "user"


def hash_email(email: str) -> str:
    """Return a deterministic hash for an email address."""

    normalized = email.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def redact_metadata(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    """Ensure metadata is serializable and free of unexpected secrets."""

    safe: dict[str, Any] = {}
    if not metadata:
        return safe
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            safe[key] = value
        elif isinstance(value, Mapping):
            safe[key] = redact_metadata(value)
        elif isinstance(value, (list, tuple)):
            safe[key] = [item for item in value if isinstance(item, (str, int, float, bool))]
        else:
            safe[key] = str(value)
    return safe


def record_admin_event(
    session: Session,
    *,
    actor_user_id: UUID,
    target_user_id: UUID,
    action: str,
    metadata: Mapping[str, Any] | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Persist an audit log entry for admin activity."""

    entry = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        target_type=AUDIT_TARGET_USER,
        target_id=str(target_user_id),
        metadata_json=redact_metadata(metadata),
        ip=ip,
        user_agent=user_agent,
        occurred_at=datetime.now(timezone.utc),
    )
    session.add(entry)
    logger.info(
        "admin.audit.recorded",
        action=action,
        actor_user_id=str(actor_user_id),
        target_user_id=str(target_user_id),
    )


__all__ = ["record_admin_event", "hash_email", "AUDIT_TARGET_USER", "redact_metadata"]
