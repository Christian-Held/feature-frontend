"""Password reset functionality with token management and email delivery."""

from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import datetime, timedelta, timezone

import structlog
from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.auth.email.tasks import enqueue_password_reset_email
from backend.auth.service.rate_limit import enforce_rate_limit
from backend.core.config import AppConfig
from backend.db.models.user import PasswordReset, User, UserStatus
from backend.redis.client import get_redis_client
from backend.security.passwords import get_password_service
from redis.asyncio import Redis

logger = structlog.get_logger(__name__)

PASSWORD_RESET_WINDOW_HOURS = 1


def _sign_reset_token(reset_id: uuid.UUID, *, secret: str) -> str:
    """Generate HMAC signature for password reset token."""
    signature = hmac.new(secret.encode("utf-8"), str(reset_id).encode("utf-8"), hashlib.sha256)
    return signature.hexdigest()


def _hash_token(signature: str) -> str:
    """Hash the signature for database storage."""
    return hashlib.sha256(signature.encode("utf-8")).hexdigest()


def _build_reset_token(record: PasswordReset, *, secret: str) -> str:
    """Build complete reset token: ID + signature."""
    signature = _sign_reset_token(record.id, secret=secret)
    return f"{record.id}.{signature}"


def _reset_url(token: str, *, settings: AppConfig) -> str:
    """Build password reset URL."""
    return f"{settings.frontend_base_url}/reset-password?token={token}"


def _store_token_hash(record: PasswordReset, *, secret: str) -> None:
    """Generate and store token hash in record."""
    signature = _sign_reset_token(record.id, secret=secret)
    record.token_hash = _hash_token(signature)


def _create_password_reset(session: Session, user: User, settings: AppConfig) -> tuple[PasswordReset, str]:
    """Create a new password reset record and return token."""
    reset = PasswordReset(
        id=uuid.uuid4(),
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=PASSWORD_RESET_WINDOW_HOURS),
    )
    _store_token_hash(reset, secret=settings.email_verification_secret)
    session.add(reset)
    session.flush()
    token = _build_reset_token(reset, secret=settings.email_verification_secret)
    return reset, token


def _existing_active_token(session: Session, user: User, *, now: datetime) -> PasswordReset | None:
    """Find existing unused non-expired reset token for user."""
    stmt = (
        select(PasswordReset)
        .where(
            PasswordReset.user_id == user.id,
            PasswordReset.used_at.is_(None),
            PasswordReset.expires_at > now,
        )
        .order_by(PasswordReset.created_at.desc())
        .limit(1)
    )
    return session.execute(stmt).scalar_one_or_none()


def _purge_tokens(session: Session, user: User) -> None:
    """Delete all password reset tokens for user."""
    stmt = delete(PasswordReset).where(PasswordReset.user_id == user.id)
    session.execute(stmt)


def _ensure_timezone(dt: datetime) -> datetime:
    """Ensure datetime has timezone info."""
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def request_password_reset(
    *,
    session: Session,
    email: str,
    settings: AppConfig,
    remote_ip: str | None,
    redis: Redis | None = None,
) -> str:
    """Handle password reset request and enqueue email."""

    email = email.lower()

    redis_client = redis or get_redis_client()
    await enforce_rate_limit(
        redis_client,
        settings=settings,
        scope="password_reset",
        identifier=remote_ip or "",
        limit=3,
        window_seconds=3600,
    )

    # Look up user - but don't reveal if they exist for security
    stmt = select(User).where(User.email == email)
    user = session.execute(stmt).scalar_one_or_none()

    if not user or user.status != UserStatus.ACTIVE:
        # Return success message even if user doesn't exist (security)
        logger.info("password_reset.no_active_user", email=email)
        return "Wenn ein Konto mit dieser E-Mail existiert, haben wir einen Link zum Zurücksetzen gesendet."

    now = datetime.now(timezone.utc)
    active_token = _existing_active_token(session, user, now=now)

    if active_token is None:
        # Create new token
        _purge_tokens(session, user)
        reset, token = _create_password_reset(session, user, settings)
        logger.info(
            "password_reset.created",
            user_id=str(user.id),
            email=email,
            reset_id=str(reset.id),
        )
    else:
        # Reuse existing valid token
        reset = active_token
        token = _build_reset_token(active_token, secret=settings.email_verification_secret)
        logger.info(
            "password_reset.reused",
            user_id=str(user.id),
            email=email,
            reset_id=str(reset.id),
        )

    reset_url = _reset_url(token, settings=settings)
    enqueue_password_reset_email(user.email, reset_url)

    return "Wenn ein Konto mit dieser E-Mail existiert, haben wir einen Link zum Zurücksetzen gesendet."


def validate_password_reset_token(session: Session, token: str, settings: AppConfig) -> PasswordReset:
    """Validate token integrity and lookup the reset record."""

    try:
        reset_id_str, signature = token.split(".")
        reset_id = uuid.UUID(reset_id_str)
    except (ValueError, AttributeError):
        logger.info("password_reset.invalid_format")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ungültiger oder abgelaufener Link zum Zurücksetzen des Passworts.",
        )

    stmt = select(PasswordReset).where(PasswordReset.id == reset_id)
    reset = session.execute(stmt).scalar_one_or_none()
    if reset is None:
        logger.info("password_reset.not_found", reset_id=reset_id_str)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ungültiger oder abgelaufener Link zum Zurücksetzen des Passworts.",
        )

    expected_hash = _hash_token(signature)
    if reset.token_hash != expected_hash:
        logger.info("password_reset.signature_mismatch", reset_id=reset_id_str)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ungültiger oder abgelaufener Link zum Zurücksetzen des Passworts.",
        )

    return reset


async def complete_password_reset(
    *,
    session: Session,
    token: str,
    new_password: str,
    settings: AppConfig,
) -> User:
    """Reset user password if token is valid."""

    reset = validate_password_reset_token(session, token, settings)

    if reset.used_at is not None:
        logger.info("password_reset.already_used", reset_id=str(reset.id))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ungültiger oder abgelaufener Link zum Zurücksetzen des Passworts.",
        )

    expires_at = _ensure_timezone(reset.expires_at)
    if expires_at <= datetime.now(timezone.utc):
        user = session.get(User, reset.user_id)
        if user:
            logger.info("password_reset.expired", user_id=str(user.id), reset_id=str(reset.id))
            _purge_tokens(session, user)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ungültiger oder abgelaufener Link zum Zurücksetzen des Passworts.",
        )

    user = session.get(User, reset.user_id)
    if not user:
        logger.info("password_reset.user_missing", reset_id=str(reset.id))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ungültiger oder abgelaufener Link zum Zurücksetzen des Passworts.",
        )

    # Update password
    password_service = get_password_service()
    user.password_hash = password_service.hash(new_password)
    reset.used_at = datetime.now(timezone.utc)
    _purge_tokens(session, user)

    logger.info(
        "password_reset.completed",
        user_id=str(user.id),
        reset_id=str(reset.id),
    )
    return user


__all__ = [
    "request_password_reset",
    "complete_password_reset",
    "validate_password_reset_token",
]
