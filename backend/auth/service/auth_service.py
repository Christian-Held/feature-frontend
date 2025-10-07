"""Core authentication services covering login, sessions, refresh, and MFA."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import structlog
from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.auth.schemas import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    RecoveryLoginRequest,
    RecoveryLoginResponse,
    RefreshRequest,
    RefreshResponse,
    TwoFAEnableCompleteRequest,
    TwoFAEnableCompleteResponse,
    TwoFAEnableInitResponse,
    TwoFADisableRequest,
    TwoFADisableResponse,
    TwoFAVerifyRequest,
    TwoFAVerifyResponse,
)
from backend.auth.service.captcha import verify_turnstile
from backend.auth.service.mfa_service import (
    build_otpauth_url,
    generate_qr_svg,
    generate_recovery_codes,
    generate_totp_secret,
    rotate_recovery_codes,
    verify_totp,
)
from backend.auth.service.rate_limit import enforce_rate_limit
from backend.auth.service.session_service import (
    create_session,
    find_session_by_refresh,
    revoke_other_sessions,
    revoke_session,
    rotate_session_refresh,
    validate_session_bindings,
)
from backend.auth.tokens import hash_token
from backend.core.config import AppConfig
from backend.db.models.audit import AuditLog
from backend.db.models.user import Session as SessionModel
from backend.db.models.user import User, UserStatus
from backend.redis.client import get_redis_client
from backend.security.encryption import EncryptionService, get_encryption_service
from backend.security.jwt_service import get_jwt_service
from backend.security.passwords import get_password_service

logger = structlog.get_logger(__name__)


def _load_mfa_secret(raw: bytes, encryption: EncryptionService) -> str:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return raw.decode("utf-8")
    if isinstance(payload, dict) and {"version", "nonce", "ciphertext"} <= payload.keys():
        return encryption.decrypt_bytes(raw).decode("utf-8")
    return raw.decode("utf-8")


def _load_recovery_codes(
    payload: list[str] | dict[str, str] | None,
    encryption: EncryptionService,
) -> list[str]:
    if payload is None:
        return []
    if isinstance(payload, dict) and {"version", "nonce", "ciphertext"} <= payload.keys():
        data = encryption.decrypt_json(payload)
        return list(data)
    if isinstance(payload, list):
        return payload
    return list(payload)


LOGIN_IP_LIMIT = 10
LOGIN_ACCOUNT_LIMIT = 5
RATE_WINDOW_SECONDS = 900
LOGIN_FAILURE_THRESHOLD = 3
LOGIN_LOCK_THRESHOLD = 5
LOGIN_LOCK_SECONDS = 300
MFA_ATTEMPT_LIMIT = 5
MFA_LOCK_SECONDS = 300
CHALLENGE_TTL_SECONDS = 300
RECOVERY_LOGIN_LIMIT = 5

CHALLENGE_PREFIX = "auth:challenge"
LOGIN_FAILURE_PREFIX = "auth:login:failures"
LOGIN_LOCK_PREFIX = "auth:login:lock"
CAPTCHA_FORCE_PREFIX = "auth:login:captcha"
MFA_ATTEMPT_PREFIX = "auth:mfa:attempts"
MFA_LOCK_PREFIX = "auth:mfa:lock"
MFA_CAPTCHA_PREFIX = "auth:mfa:captcha"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _redis(redis: Redis | None) -> Redis:
    return redis or get_redis_client()


def _login_failure_key(email: str) -> str:
    return f"{LOGIN_FAILURE_PREFIX}:{email}"


def _login_lock_key(email: str) -> str:
    return f"{LOGIN_LOCK_PREFIX}:{email}"


def _captcha_force_key(identifier: str) -> str:
    return f"{CAPTCHA_FORCE_PREFIX}:{identifier}"


def _challenge_key(challenge_id: str) -> str:
    return f"{CHALLENGE_PREFIX}:{challenge_id}"


def _mfa_attempts_key(user_id: uuid.UUID) -> str:
    return f"{MFA_ATTEMPT_PREFIX}:{user_id}"


def _mfa_lock_key(user_id: uuid.UUID) -> str:
    return f"{MFA_LOCK_PREFIX}:{user_id}"


def _mfa_captcha_key(user_id: uuid.UUID) -> str:
    return f"{MFA_CAPTCHA_PREFIX}:{user_id}"


async def _record_login_failure(redis: Redis, email: str) -> int:
    key = _login_failure_key(email)
    failures = await redis.incr(key)
    if failures == 1:
        await redis.expire(key, RATE_WINDOW_SECONDS)
    if failures >= LOGIN_FAILURE_THRESHOLD:
        await redis.set(_captcha_force_key(email), "1", ex=RATE_WINDOW_SECONDS)
    if failures >= LOGIN_LOCK_THRESHOLD:
        await redis.set(_login_lock_key(email), "1", ex=LOGIN_LOCK_SECONDS)
    return failures


async def _clear_login_state(redis: Redis, email: str) -> None:
    await redis.delete(
        _login_failure_key(email),
        _login_lock_key(email),
        _captcha_force_key(email),
    )


async def _requires_captcha(redis: Redis, email: str, user_id: uuid.UUID | None = None) -> bool:
    if await redis.get(_captcha_force_key(email)):
        return True
    if user_id and await redis.get(_mfa_captcha_key(user_id)):
        return True
    return False


async def _ensure_not_locked(redis: Redis, email: str, user_id: uuid.UUID | None = None) -> None:
    if await redis.get(_login_lock_key(email)):
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account temporarily locked. Please try again later.",
        )
    if user_id and await redis.get(_mfa_lock_key(user_id)):
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account temporarily locked. Please try again later.",
        )


def _audit(
    db: Session,
    *,
    user_id: uuid.UUID | None,
    action: str,
    ip: str | None,
    user_agent: str | None,
    metadata: dict | None = None,
) -> None:
    entry = AuditLog(
        actor_user_id=user_id,
        action=action,
        target_type="user",
        target_id=str(user_id) if user_id else None,
        ip=ip,
        user_agent=user_agent,
        metadata_json=metadata,
        occurred_at=_utcnow(),
    )
    db.add(entry)


async def login_user(
    *,
    db: Session,
    settings: AppConfig,
    request: LoginRequest,
    redis: Redis | None,
    user_agent: str | None,
    ip_address: str | None,
) -> LoginResponse:
    redis_client = _redis(redis)
    email = request.email.lower()

    await enforce_rate_limit(
        redis_client,
        settings=settings,
        scope="login:ip",
        identifier=ip_address or "",
        limit=LOGIN_IP_LIMIT,
        window_seconds=RATE_WINDOW_SECONDS,
    )
    await enforce_rate_limit(
        redis_client,
        settings=settings,
        scope="login:account",
        identifier=email,
        limit=LOGIN_ACCOUNT_LIMIT,
        window_seconds=RATE_WINDOW_SECONDS,
    )

    await _ensure_not_locked(redis_client, email)

    if await _requires_captcha(redis_client, email):
        if not request.captcha_token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Captcha required.")
        await verify_turnstile(
            captcha_token=request.captcha_token,
            settings=settings,
            remote_ip=ip_address,
        )

    stmt = select(User).where(User.email == email)
    user = db.execute(stmt).scalar_one_or_none()
    encryption = get_encryption_service()
    encryption = get_encryption_service()
    encryption = get_encryption_service()
    password_service = get_password_service()
    raw_password = request.password.get_secret_value()

    if not user or not password_service.verify(user.password_hash, raw_password):
        await _record_login_failure(redis_client, email)
        _audit(
            db,
            user_id=user.id if user else None,
            action="login_failure",
            ip=ip_address,
            user_agent=user_agent,
            metadata={"email": email},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email or password is incorrect.")

    await _ensure_not_locked(redis_client, email, user.id)

    if user.status == UserStatus.UNVERIFIED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must confirm your registration first. We’ve sent you an email.",
        )
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don’t have permission to perform this action.")

    await _clear_login_state(redis_client, email)

    if await _requires_captcha(redis_client, email, user.id):
        if not request.captcha_token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Captcha required.")
        await verify_turnstile(
            captcha_token=request.captcha_token,
            settings=settings,
            remote_ip=ip_address,
        )

    if user.mfa_enabled:
        challenge_id = str(uuid.uuid4())
        payload = {
            "type": "login",
            "user_id": str(user.id),
            "email": user.email,
            "ip": ip_address,
            "ua": user_agent,
            "created_at": _utcnow().isoformat(),
        }
        await redis_client.set(_challenge_key(challenge_id), json.dumps(payload), ex=CHALLENGE_TTL_SECONDS)
        logger.info("auth.login.challenge", user_id=str(user.id), challenge_id=challenge_id)
        return LoginResponse(requires_2fa=True, challenge_id=challenge_id)

    jwt_service = get_jwt_service()
    access_token = jwt_service.issue_access_token(str(user.id))
    refresh_token = jwt_service.issue_refresh_token(str(user.id))
    session_record = create_session(
        db=db,
        user_id=user.id,
        refresh_token=refresh_token,
        settings=settings,
        user_agent=user_agent,
        ip=ip_address,
    )

    user.last_login_at = _utcnow()
    user.last_ip = ip_address

    _audit(
        db,
        user_id=user.id,
        action="login_success",
        ip=ip_address,
        user_agent=user_agent,
        metadata={"session_id": str(session_record.id)},
    )

    db.commit()

    return LoginResponse(
        requires_2fa=False,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_ttl_seconds,
    )


async def verify_two_factor(
    *,
    db: Session,
    settings: AppConfig,
    request: TwoFAVerifyRequest,
    redis: Redis | None,
    user_agent: str | None,
    ip_address: str | None,
) -> TwoFAVerifyResponse:
    redis_client = _redis(redis)
    challenge_raw = await redis_client.get(_challenge_key(request.challenge_id))
    if not challenge_raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired challenge.")
    challenge = json.loads(challenge_raw)
    if challenge.get("type") != "login":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired challenge.")

    user_id = uuid.UUID(challenge["user_id"])
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired challenge.")

    await _ensure_not_locked(redis_client, user.email, user.id)

    await enforce_rate_limit(
        redis_client,
        settings=settings,
        scope="2fa",
        identifier=str(user.id),
        limit=10,
        window_seconds=RATE_WINDOW_SECONDS,
    )

    if await _requires_captcha(redis_client, user.email, user.id):
        if not request.captcha_token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Captcha required.")
        await verify_turnstile(
            captcha_token=request.captcha_token,
            settings=settings,
            remote_ip=ip_address,
        )

    if not user.mfa_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired challenge.")

    encryption = get_encryption_service()
    secret = _load_mfa_secret(user.mfa_secret, encryption)
    if not verify_totp(secret=secret, otp=request.otp):
        attempts_key = _mfa_attempts_key(user.id)
        attempts = await redis_client.incr(attempts_key)
        if attempts == 1:
            await redis_client.expire(attempts_key, MFA_LOCK_SECONDS)
        if attempts >= MFA_ATTEMPT_LIMIT:
            await redis_client.set(_mfa_captcha_key(user.id), "1", ex=MFA_LOCK_SECONDS)
            await redis_client.set(_mfa_lock_key(user.id), "1", ex=MFA_LOCK_SECONDS)
        _audit(
            db,
            user_id=user.id,
            action="totp_failure",
            ip=ip_address,
            user_agent=user_agent,
            metadata={"challenge_id": request.challenge_id},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid security code.")

    await redis_client.delete(
        _challenge_key(request.challenge_id),
        _mfa_attempts_key(user.id),
        _mfa_captcha_key(user.id),
        _mfa_lock_key(user.id),
    )
    await _clear_login_state(redis_client, user.email)

    jwt_service = get_jwt_service()
    access_token = jwt_service.issue_access_token(str(user.id))
    refresh_token = jwt_service.issue_refresh_token(str(user.id))
    session_record = create_session(
        db=db,
        user_id=user.id,
        refresh_token=refresh_token,
        settings=settings,
        user_agent=user_agent or challenge.get("ua"),
        ip=ip_address or challenge.get("ip"),
    )

    user.last_login_at = _utcnow()
    user.last_ip = ip_address or challenge.get("ip")

    _audit(
        db,
        user_id=user.id,
        action="login_success",
        ip=ip_address or challenge.get("ip"),
        user_agent=user_agent or challenge.get("ua"),
        metadata={"session_id": str(session_record.id), "mfa": True},
    )

    db.commit()

    return TwoFAVerifyResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_ttl_seconds,
    )


async def refresh_tokens(
    *,
    db: Session,
    settings: AppConfig,
    request: RefreshRequest,
    redis: Redis | None,
    user_agent: str | None,
    ip_address: str | None,
) -> RefreshResponse:
    token = request.refresh_token
    session_record = find_session_by_refresh(db, token)
    if not session_record or session_record.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You don’t have permission to perform this action.")

    if _ensure_aware(session_record.expires_at) <= _utcnow():
        revoke_session(db, session_record)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You don’t have permission to perform this action.")

    if not validate_session_bindings(session_record=session_record, user_agent=user_agent, ip=ip_address):
        revoke_session(db, session_record)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You don’t have permission to perform this action.")

    jwt_service = get_jwt_service()
    try:
        payload = jwt_service.decode(token)
    except Exception as exc:  # pragma: no cover - jwt library raises various
        logger.info("auth.refresh.invalid_token", error=str(exc))
        revoke_session(db, session_record)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You don’t have permission to perform this action.")

    if payload.get("type") != "refresh":
        revoke_session(db, session_record)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You don’t have permission to perform this action.")

    user_id = payload.get("sub")
    user = db.get(User, uuid.UUID(user_id)) if user_id else None
    if not user:
        revoke_session(db, session_record)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You don’t have permission to perform this action.")

    access_token = jwt_service.issue_access_token(str(user.id))
    new_refresh = jwt_service.issue_refresh_token(str(user.id))
    rotate_session_refresh(db=db, session_record=session_record, new_refresh_token=new_refresh, settings=settings)

    _audit(
        db,
        user_id=user.id,
        action="refresh_rotated",
        ip=ip_address,
        user_agent=user_agent,
        metadata={"session_id": str(session_record.id)},
    )

    db.commit()

    return RefreshResponse(access_token=access_token, refresh_token=new_refresh, expires_in=settings.jwt_access_ttl_seconds)


async def logout_session(
    *,
    db: Session,
    token: str,
    user_agent: str | None,
    ip_address: str | None,
) -> LogoutResponse:
    session_record = find_session_by_refresh(db, token)
    if not session_record:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You don’t have permission to perform this action.")
    revoke_session(db, session_record)
    user_id = session_record.user_id
    _audit(
        db,
        user_id=user_id,
        action="logout",
        ip=ip_address,
        user_agent=user_agent,
        metadata={"session_id": str(session_record.id)},
    )
    db.commit()
    return LogoutResponse(message="Logged out.")


async def sign_out_other_sessions(
    *,
    db: Session,
    user: User,
    active_session: SessionModel | None = None,
) -> int:
    count = revoke_other_sessions(db, user.id, active_session.id if active_session else None)
    if count:
        _audit(
            db,
            user_id=user.id,
            action="logout",
            ip=None,
            user_agent=None,
            metadata={"sign_out_others": True, "revoked": count},
        )
        db.commit()
    return count


async def init_two_factor(
    *,
    db: Session,
    settings: AppConfig,
    user: User,
    redis: Redis | None,
) -> TwoFAEnableInitResponse:
    redis_client = _redis(redis)
    secret = generate_totp_secret()
    otpauth_url = build_otpauth_url(secret=secret, email=user.email, issuer=settings.jwt_issuer)
    qr_svg = generate_qr_svg(otpauth_url)
    challenge_id = str(uuid.uuid4())
    payload = {
        "type": "mfa_enable",
        "user_id": str(user.id),
        "secret": secret,
    }
    await redis_client.set(_challenge_key(challenge_id), json.dumps(payload), ex=CHALLENGE_TTL_SECONDS)
    logger.info("auth.mfa.enable_init", user_id=str(user.id), challenge_id=challenge_id)
    return TwoFAEnableInitResponse(secret=secret, otpauth_url=otpauth_url, qr_svg=qr_svg, challenge_id=challenge_id)


async def complete_two_factor(
    *,
    db: Session,
    request: TwoFAEnableCompleteRequest,
    user: User,
    redis: Redis | None,
) -> TwoFAEnableCompleteResponse:
    redis_client = _redis(redis)
    data_raw = await redis_client.get(_challenge_key(request.challenge_id))
    if not data_raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired challenge.")
    data = json.loads(data_raw)
    if data.get("type") != "mfa_enable" or data.get("user_id") != str(user.id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired challenge.")

    secret = data["secret"]
    if not verify_totp(secret=secret, otp=request.otp):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid security code.")

    codes, hashed_codes = generate_recovery_codes()
    encryption = get_encryption_service()
    user.mfa_enabled = True
    user.mfa_secret = encryption.encrypt_bytes(secret.encode("utf-8"))
    user.recovery_codes = encryption.encrypt_json(hashed_codes)
    await redis_client.delete(_challenge_key(request.challenge_id))

    db.commit()
    logger.info("auth.mfa.enabled", user_id=str(user.id))
    return TwoFAEnableCompleteResponse(recovery_codes=codes)


async def disable_two_factor(
    *,
    db: Session,
    user: User,
    request: TwoFADisableRequest,
) -> TwoFADisableResponse:
    password_service = get_password_service()
    if not password_service.verify(user.password_hash, request.password.get_secret_value()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email or password is incorrect.")
    if not user.mfa_secret:
        return TwoFADisableResponse(message="Two-factor authentication already disabled.")

    encryption = get_encryption_service()
    secret = _load_mfa_secret(user.mfa_secret, encryption)
    if not verify_totp(secret=secret, otp=request.otp):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid security code.")

    user.mfa_enabled = False
    user.mfa_secret = None
    user.recovery_codes = None
    db.commit()
    logger.info("auth.mfa.disabled", user_id=str(user.id))
    return TwoFADisableResponse(message="Two-factor authentication disabled.")


async def recovery_login(
    *,
    db: Session,
    settings: AppConfig,
    request: RecoveryLoginRequest,
    redis: Redis | None,
    user_agent: str | None,
    ip_address: str | None,
) -> RecoveryLoginResponse:
    redis_client = _redis(redis)
    email = request.email.lower()

    await enforce_rate_limit(
        redis_client,
        settings=settings,
        scope="recovery_login",
        identifier=email,
        limit=RECOVERY_LOGIN_LIMIT,
        window_seconds=RATE_WINDOW_SECONDS,
    )

    stmt = select(User).where(User.email == email)
    user = db.execute(stmt).scalar_one_or_none()
    if not user or not user.mfa_enabled:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email or password is incorrect.")

    await _ensure_not_locked(redis_client, email, user.id)

    encryption = get_encryption_service()
    password_service = get_password_service()
    if request.password:
        if not password_service.verify(user.password_hash, request.password.get_secret_value()):
            await _record_login_failure(redis_client, email)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email or password is incorrect.")
    elif request.challenge_id:
        data_raw = await redis_client.get(_challenge_key(request.challenge_id))
        if not data_raw:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired challenge.")
        data = json.loads(data_raw)
        if data.get("type") != "login" or data.get("user_id") != str(user.id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired challenge.")
    else:  # pragma: no cover - validation should prevent
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request.")

    hashed_codes = _load_recovery_codes(user.recovery_codes, encryption)
    code_hash = hash_token(request.recovery_code)
    if code_hash not in hashed_codes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid security code.")

    remaining = rotate_recovery_codes(hashed_codes, code_hash)
    user.recovery_codes = encryption.encrypt_json(remaining)

    jwt_service = get_jwt_service()
    access_token = jwt_service.issue_access_token(str(user.id))
    refresh_token = jwt_service.issue_refresh_token(str(user.id))
    session_record = create_session(
        db=db,
        user_id=user.id,
        refresh_token=refresh_token,
        settings=settings,
        user_agent=user_agent,
        ip=ip_address,
    )

    if request.challenge_id:
        await redis_client.delete(_challenge_key(request.challenge_id))
    await _clear_login_state(redis_client, email)

    _audit(
        db,
        user_id=user.id,
        action="recovery_login_used",
        ip=ip_address,
        user_agent=user_agent,
        metadata={"session_id": str(session_record.id)},
    )

    db.commit()

    return RecoveryLoginResponse(access_token=access_token, refresh_token=refresh_token, expires_in=settings.jwt_access_ttl_seconds)
