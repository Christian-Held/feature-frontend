"""Registration and verification token lifecycle management."""

from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import datetime, timedelta, timezone

import structlog
from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.auth.email.tasks import enqueue_verification_email
from backend.auth.schemas.registration import RegistrationRequest, ResendVerificationRequest
from backend.auth.service.captcha import verify_turnstile
from backend.auth.service.rate_limit import enforce_rate_limit
from backend.core.config import AppConfig
from backend.db.models.user import EmailVerification, User, UserStatus
from backend.redis.client import get_redis_client
from backend.security.passwords import get_password_service

logger = structlog.get_logger(__name__)

VERIFICATION_WINDOW_HOURS = 24


def _sign_verification_token(verification_id: uuid.UUID, *, secret: str) -> str:
    signature = hmac.new(secret.encode("utf-8"), str(verification_id).encode("utf-8"), hashlib.sha256)
    return signature.hexdigest()


def _hash_token(signature: str) -> str:
    return hashlib.sha256(signature.encode("utf-8")).hexdigest()


def _build_verification_token(record: EmailVerification, *, secret: str) -> str:
    signature = _sign_verification_token(record.id, secret=secret)
    return f"{record.id}.{signature}"


def _verification_url(token: str, *, settings: AppConfig) -> str:
    return f"{settings.api_base_url}/v1/auth/verify-email?token={token}"


def _store_token_hash(record: EmailVerification, *, secret: str) -> None:
    signature = _sign_verification_token(record.id, secret=secret)
    record.token_hash = _hash_token(signature)


def _create_email_verification(session: Session, user: User, settings: AppConfig) -> tuple[EmailVerification, str]:
    verification = EmailVerification(
        id=uuid.uuid4(),
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=VERIFICATION_WINDOW_HOURS),
    )
    _store_token_hash(verification, secret=settings.email_verification_secret)
    session.add(verification)
    session.flush()
    token = _build_verification_token(verification, secret=settings.email_verification_secret)
    return verification, token


def _existing_active_token(session: Session, user: User, *, now: datetime) -> EmailVerification | None:
    stmt = (
        select(EmailVerification)
        .where(
            EmailVerification.user_id == user.id,
            EmailVerification.used_at.is_(None),
            EmailVerification.expires_at > now,
        )
        .order_by(EmailVerification.created_at.desc())
        .limit(1)
    )
    return session.execute(stmt).scalar_one_or_none()


def _purge_tokens(session: Session, user: User) -> None:
    stmt = delete(EmailVerification).where(EmailVerification.user_id == user.id)
    session.execute(stmt)


def _ensure_timezone(dt: datetime) -> datetime:
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def register_user(
    *,
    session: Session,
    request: RegistrationRequest,
    settings: AppConfig,
    remote_ip: str | None,
    http_client=None,
    redis: Redis | None = None,
) -> str:
    """Handle registration flow and enqueue verification email."""

    await verify_turnstile(
        captcha_token=request.captcha_token,
        settings=settings,
        remote_ip=remote_ip,
        http_client=http_client,
    )

    redis_client = redis or get_redis_client()
    await enforce_rate_limit(
        redis_client,
        settings=settings,
        scope="register",
        identifier=remote_ip or "",
        limit=5,
        window_seconds=3600,
    )

    email = request.email.lower()
    password_service = get_password_service()
    raw_password = request.password.get_secret_value()
    hashed_password = password_service.hash(raw_password)

    stmt = select(User).where(User.email == email)
    user = session.execute(stmt).scalar_one_or_none()
    now = datetime.now(timezone.utc)

    if user and user.status == UserStatus.ACTIVE and user.email_verified_at is not None:
        logger.info("registration.email_already_verified", email=email)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    message = "Registrierung fast abgeschlossen — bitte bestätige deine E-Mail. Der Link ist 24 Stunden gültig."

    if user:
        logger.info("registration.unverified_retry", user_id=str(user.id), email=email)
        active_token = _existing_active_token(session, user, now=now)
        if active_token is None:
            _purge_tokens(session, user)
            user.password_hash = hashed_password
            verification, token = _create_email_verification(session, user, settings)
            verification_url = _verification_url(token, settings=settings)
            enqueue_verification_email(user.email, verification_url)
            logger.info(
                "registration.verification_reissued",
                user_id=str(user.id),
                email=email,
                verification_id=str(verification.id),
            )
            return message

        token = _build_verification_token(active_token, secret=settings.email_verification_secret)
        verification_url = _verification_url(token, settings=settings)
        enqueue_verification_email(user.email, verification_url)
        logger.info(
            "registration.verification_resent",
            user_id=str(user.id),
            email=email,
            verification_id=str(active_token.id),
        )
        return message

    user = User(
        email=email,
        status=UserStatus.UNVERIFIED,
        password_hash=hashed_password,
    )
    session.add(user)
    session.flush()

    verification, token = _create_email_verification(session, user, settings)
    verification_url = _verification_url(token, settings=settings)
    enqueue_verification_email(user.email, verification_url)

    logger.info(
        "registration.created",
        user_id=str(user.id),
        email=email,
        verification_id=str(verification.id),
    )
    return message


async def resend_verification(
    *,
    session: Session,
    request: ResendVerificationRequest,
    settings: AppConfig,
    redis: Redis | None = None,
) -> str:
    """Handle resend verification flow with rate limiting."""

    email = request.email.lower()

    stmt = select(User).where(User.email == email)
    user = session.execute(stmt).scalar_one_or_none()
    if not user or user.status != UserStatus.UNVERIFIED:
        logger.info("registration.resend.no_unverified_user", email=email)
        return "Wenn ein Konto mit dieser E-Mail existiert, haben wir den Link erneut gesendet."

    redis_client = redis or get_redis_client()
    await enforce_rate_limit(
        redis_client,
        settings=settings,
        scope="resend_verification",
        identifier=str(user.id),
        limit=3,
        window_seconds=86400,
    )

    now = datetime.now(timezone.utc)
    active_token = _existing_active_token(session, user, now=now)
    if active_token is None:
        _purge_tokens(session, user)
        verification, token = _create_email_verification(session, user, settings)
        logger.info(
            "registration.resend.new_token",
            user_id=str(user.id),
            email=email,
            verification_id=str(verification.id),
        )
    else:
        verification = active_token
        token = _build_verification_token(active_token, secret=settings.email_verification_secret)
        logger.info(
            "registration.resend.existing_token",
            user_id=str(user.id),
            email=email,
            verification_id=str(verification.id),
        )

    verification_url = _verification_url(token, settings=settings)
    enqueue_verification_email(user.email, verification_url)
    return "Registrierung fast abgeschlossen — bitte bestätige deine E-Mail. Der Link ist 24 Stunden gültig."


def validate_email_verification_token(session: Session, token: str, settings: AppConfig) -> EmailVerification:
    """Validate token integrity and lookup the verification record."""

    try:
        verification_id_str, signature = token.split(".")
        verification_id = uuid.UUID(verification_id_str)
    except (ValueError, AttributeError):
        logger.info("verification.invalid_format")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ungültiger oder abgelaufener Bestätigungslink.")

    stmt = select(EmailVerification).where(EmailVerification.id == verification_id)
    verification = session.execute(stmt).scalar_one_or_none()
    if verification is None:
        logger.info("verification.not_found", verification_id=verification_id_str)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ungültiger oder abgelaufener Bestätigungslink.")

    expected_hash = _hash_token(signature)
    if verification.token_hash != expected_hash:
        logger.info("verification.signature_mismatch", verification_id=verification_id_str)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ungültiger oder abgelaufener Bestätigungslink.")

    return verification


async def complete_email_verification(
    *,
    session: Session,
    token: str,
    settings: AppConfig,
) -> tuple[User, EmailVerification, bool]:
    """Mark verification as complete if token valid; return whether expired."""

    verification = validate_email_verification_token(session, token, settings)

    if verification.used_at is not None:
        logger.info("verification.already_used", verification_id=str(verification.id))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ungültiger oder abgelaufener Bestätigungslink.")

    expires_at = _ensure_timezone(verification.expires_at)
    if expires_at <= datetime.now(timezone.utc):
        user = session.get(User, verification.user_id)
        if user:
            logger.info("verification.expired", user_id=str(user.id), verification_id=str(verification.id))
            _purge_tokens(session, user)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ungültiger oder abgelaufener Bestätigungslink.")

    user = session.get(User, verification.user_id)
    if not user:
        logger.info("verification.user_missing", verification_id=str(verification.id))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ungültiger oder abgelaufener Bestätigungslink.")

    user.status = UserStatus.ACTIVE
    user.email_verified_at = datetime.now(timezone.utc)
    verification.used_at = datetime.now(timezone.utc)
    _purge_tokens(session, user)

    logger.info(
        "verification.completed",
        user_id=str(user.id),
        verification_id=str(verification.id),
    )
    return user, verification, True


__all__ = [
    "register_user",
    "resend_verification",
    "complete_email_verification",
    "validate_email_verification_token",
]
