"""Session persistence helpers for refresh token lifecycle management."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from ipaddress import ip_address, IPv4Address
import uuid

import structlog
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.auth.tokens import hash_token
from backend.core.config import AppConfig
from backend.db.models.user import Session as SessionModel

logger = structlog.get_logger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_ip(ip: str | None) -> str | None:
    if not ip:
        return None
    try:
        addr = ip_address(ip)
    except ValueError:
        return ip
    if isinstance(addr, IPv4Address):
        octets = ip.split(".")
        return ".".join(octets[:3]) + ".0/24"
    return str(addr)


def create_session(
    *,
    db: Session,
    user_id: uuid.UUID,
    refresh_token: str,
    settings: AppConfig,
    user_agent: str | None,
    ip: str | None,
) -> SessionModel:
    """Persist a new session bound to the given refresh token."""

    now = _utcnow()
    expires_at = now + timedelta(seconds=settings.jwt_refresh_ttl_seconds)
    session_record = SessionModel(
        user_id=user_id,
        refresh_token_hash=hash_token(refresh_token),
        expires_at=expires_at,
        user_agent=user_agent[:512] if user_agent else None,
        ip=_normalize_ip(ip),
    )
    db.add(session_record)
    db.flush()
    logger.info(
        "session.created",
        session_id=str(session_record.id),
        user_id=str(user_id),
        ip=session_record.ip,
    )
    return session_record


def find_session_by_refresh(db: Session, refresh_token: str) -> SessionModel | None:
    hashed = hash_token(refresh_token)
    stmt = select(SessionModel).where(SessionModel.refresh_token_hash == hashed)
    return db.execute(stmt).scalar_one_or_none()


def rotate_session_refresh(
    *,
    db: Session,
    session_record: SessionModel,
    new_refresh_token: str,
    settings: AppConfig,
) -> None:
    now = _utcnow()
    session_record.refresh_token_hash = hash_token(new_refresh_token)
    session_record.expires_at = now + timedelta(seconds=settings.jwt_refresh_ttl_seconds)
    session_record.rotated_at = now
    db.flush()
    logger.info(
        "session.refresh_rotated",
        session_id=str(session_record.id),
        user_id=str(session_record.user_id),
    )


def revoke_session(db: Session, session_record: SessionModel) -> None:
    if session_record.revoked_at:
        return
    session_record.revoked_at = _utcnow()
    db.flush()
    logger.info(
        "session.revoked",
        session_id=str(session_record.id),
        user_id=str(session_record.user_id),
    )


def revoke_other_sessions(db: Session, user_id: uuid.UUID, active_session_id: uuid.UUID | None = None) -> int:
    """Revoke all sessions for the user except the active one."""

    now = _utcnow()
    stmt = (
        update(SessionModel)
        .where(SessionModel.user_id == user_id)
        .where(SessionModel.revoked_at.is_(None))
    )
    if active_session_id:
        stmt = stmt.where(SessionModel.id != active_session_id)
    result = db.execute(stmt.values(revoked_at=now))
    db.flush()
    count = result.rowcount or 0
    if count:
        logger.info("session.revoked_others", user_id=str(user_id), count=count)
    return count


def validate_session_bindings(
    *,
    session_record: SessionModel,
    user_agent: str | None,
    ip: str | None,
) -> bool:
    """Ensure the provided client context matches the stored bindings."""

    normalized_ip = _normalize_ip(ip)
    ua_ok = (session_record.user_agent or "") == (user_agent or "")
    ip_ok = (session_record.ip or "") == (normalized_ip or "")
    return ua_ok and ip_ok


__all__ = [
    "create_session",
    "find_session_by_refresh",
    "rotate_session_refresh",
    "revoke_session",
    "revoke_other_sessions",
    "validate_session_bindings",
]
