from datetime import datetime, timezone

import pyotp
import pytest
import pytest_asyncio
from fakeredis import aioredis
from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend.auth.schemas import (
    LoginRequest,
    RecoveryLoginRequest,
    RefreshRequest,
    TwoFAVerifyRequest,
)
from backend.auth.service import auth_service
from backend.auth.service.auth_service import (
    login_user,
    logout_session,
    recovery_login,
    refresh_tokens,
    sign_out_other_sessions,
    verify_two_factor,
)
from backend.auth.tokens import hash_token
from backend.db.base import Base
from backend.db.models.user import Session as SessionModel
from backend.db.models.user import User, UserStatus
from backend.security.encryption import get_encryption_service
from backend.security.passwords import get_password_service


@pytest.fixture
def db_session(settings_env) -> Session:
    from sqlalchemy import create_engine

    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, future=True
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest_asyncio.fixture
async def fake_redis() -> aioredis.FakeRedis:
    client = aioredis.FakeRedis()
    try:
        yield client
    finally:
        await client.aclose()


@pytest.fixture(autouse=True)
def patch_captcha(monkeypatch):
    async def _noop(**kwargs):  # pragma: no cover - patched behavior
        return None

    monkeypatch.setattr(auth_service, "verify_turnstile", _noop)


def _create_user(
    session: Session,
    *,
    email: str,
    password: str,
    mfa_secret: str | None = None,
    recovery_codes: list[str] | None = None,
) -> User:
    password_service = get_password_service()
    encryption = get_encryption_service()
    encrypted_secret = (
        encryption.encrypt_bytes(mfa_secret.encode("utf-8")) if mfa_secret else None
    )
    encrypted_codes = (
        encryption.encrypt_json(recovery_codes) if recovery_codes else None
    )
    user = User(
        email=email,
        status=UserStatus.ACTIVE,
        email_verified_at=datetime.now(timezone.utc),
        password_hash=password_service.hash(password),
        mfa_enabled=bool(mfa_secret),
        mfa_secret=encrypted_secret,
        recovery_codes=encrypted_codes,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_recovery_login_requires_password_or_challenge_validation():
    with pytest.raises(ValidationError):
        RecoveryLoginRequest(email="invalid@example.com", recoveryCode="CODE-1234")


@pytest.mark.asyncio
async def test_password_login_success(db_session: Session, settings_env, fake_redis):
    _create_user(db_session, email="alice@example.com", password="SuperSecret!23")

    request = LoginRequest(email="alice@example.com", password="SuperSecret!23")
    response = await login_user(
        db=db_session,
        settings=settings_env,
        request=request,
        redis=fake_redis,
        user_agent="pytest",
        ip_address="203.0.113.10",
    )

    assert response.requires_2fa is False
    assert response.access_token
    assert response.refresh_token

    session_record = db_session.execute(select(SessionModel)).scalar_one()
    assert session_record.user_agent == "pytest"


@pytest.mark.asyncio
async def test_login_with_2fa_flow(db_session: Session, settings_env, fake_redis):
    secret = pyotp.random_base32()
    _create_user(
        db_session, email="bob@example.com", password="Secure!12345", mfa_secret=secret
    )

    login_response = await login_user(
        db=db_session,
        settings=settings_env,
        request=LoginRequest(email="bob@example.com", password="Secure!12345"),
        redis=fake_redis,
        user_agent="pytest",
        ip_address="198.51.100.77",
    )

    assert login_response.requires_2fa is True
    totp = pyotp.TOTP(secret)
    verify_response = await verify_two_factor(
        db=db_session,
        settings=settings_env,
        request=TwoFAVerifyRequest(
            challenge_id=login_response.challenge_id, otp=totp.now()
        ),
        redis=fake_redis,
        user_agent="pytest",
        ip_address="198.51.100.77",
    )

    assert verify_response.access_token
    assert verify_response.refresh_token
    sessions = db_session.execute(select(SessionModel)).scalars().all()
    assert len(sessions) == 1


@pytest.mark.asyncio
async def test_refresh_rotation_revokes_old_token(
    db_session: Session, settings_env, fake_redis
):
    _create_user(db_session, email="carol@example.com", password="Password!234")
    login_response = await login_user(
        db=db_session,
        settings=settings_env,
        request=LoginRequest(email="carol@example.com", password="Password!234"),
        redis=fake_redis,
        user_agent="pytest",
        ip_address="203.0.113.20",
    )

    refresh_response = await refresh_tokens(
        db=db_session,
        settings=settings_env,
        request=RefreshRequest(refresh_token=login_response.refresh_token),
        redis=fake_redis,
        user_agent="pytest",
        ip_address="203.0.113.20",
    )

    assert refresh_response.refresh_token != login_response.refresh_token

    with pytest.raises(HTTPException) as exc:
        await refresh_tokens(
            db=db_session,
            settings=settings_env,
            request=RefreshRequest(refresh_token=login_response.refresh_token),
            redis=fake_redis,
            user_agent="pytest",
            ip_address="203.0.113.20",
        )
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_adaptive_captcha_trigger(db_session: Session, settings_env, fake_redis):
    _create_user(db_session, email="dave@example.com", password="AnotherSecret!56")

    wrong_request = LoginRequest(email="dave@example.com", password="BadPassword")
    for _ in range(3):
        with pytest.raises(HTTPException):
            await login_user(
                db=db_session,
                settings=settings_env,
                request=wrong_request,
                redis=fake_redis,
                user_agent="pytest",
                ip_address="203.0.113.30",
            )

    with pytest.raises(HTTPException) as exc:
        await login_user(
            db=db_session,
            settings=settings_env,
            request=LoginRequest(email="dave@example.com", password="AnotherSecret!56"),
            redis=fake_redis,
            user_agent="pytest",
            ip_address="203.0.113.30",
        )
    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.detail == "Captcha required."

    success = await login_user(
        db=db_session,
        settings=settings_env,
        request=LoginRequest(
            email="dave@example.com", password="AnotherSecret!56", captchaToken="token"
        ),
        redis=fake_redis,
        user_agent="pytest",
        ip_address="203.0.113.30",
    )
    assert success.access_token


@pytest.mark.asyncio
async def test_recovery_login_requires_password_or_challenge(
    db_session: Session, settings_env, fake_redis
):
    secret = pyotp.random_base32()
    code_plain = "ABCD-EF12-3456"
    hashed_codes = [hash_token(code_plain)] + [
        hash_token(f"CODE-{i}") for i in range(1, 10)
    ]
    user = _create_user(
        db_session,
        email="eve@example.com",
        password="RecoverySecret!78",
        mfa_secret=secret,
        recovery_codes=hashed_codes,
    )

    request = RecoveryLoginRequest(
        email="eve@example.com", password="RecoverySecret!78", recoveryCode=code_plain
    )
    response = await recovery_login(
        db=db_session,
        settings=settings_env,
        request=request,
        redis=fake_redis,
        user_agent="pytest",
        ip_address="198.51.100.5",
    )
    assert response.refresh_token
    assert len(_get_recovery_codes(user)) == 9

    with pytest.raises(HTTPException):
        await recovery_login(
            db=db_session,
            settings=settings_env,
            request=RecoveryLoginRequest(
                email="eve@example.com",
                password="RecoverySecret!78",
                recoveryCode=code_plain,
            ),
            redis=fake_redis,
            user_agent="pytest",
            ip_address="198.51.100.5",
        )

    # Challenge-based recovery
    second_code = "WXYZ-AB34-5678"
    codes = _get_recovery_codes(user)
    codes.append(hash_token(second_code))
    encryption = get_encryption_service()
    user.recovery_codes = encryption.encrypt_json(codes)
    db_session.commit()

    login_response = await login_user(
        db=db_session,
        settings=settings_env,
        request=LoginRequest(email="eve@example.com", password="RecoverySecret!78"),
        redis=fake_redis,
        user_agent="pytest",
        ip_address="198.51.100.5",
    )
    recovery_response = await recovery_login(
        db=db_session,
        settings=settings_env,
        request=RecoveryLoginRequest(
            email="eve@example.com",
            challengeId=login_response.challenge_id,
            recoveryCode=second_code,
        ),
        redis=fake_redis,
        user_agent="pytest",
        ip_address="198.51.100.5",
    )
    assert recovery_response.access_token


@pytest.mark.asyncio
async def test_totp_lock_after_failures(db_session: Session, settings_env, fake_redis):
    secret = pyotp.random_base32()
    _create_user(
        db_session,
        email="frank@example.com",
        password="LockSecret!23",
        mfa_secret=secret,
    )

    login_response = await login_user(
        db=db_session,
        settings=settings_env,
        request=LoginRequest(email="frank@example.com", password="LockSecret!23"),
        redis=fake_redis,
        user_agent="pytest",
        ip_address="203.0.113.40",
    )

    for _ in range(5):
        with pytest.raises(HTTPException) as exc:
            await verify_two_factor(
                db=db_session,
                settings=settings_env,
                request=TwoFAVerifyRequest(
                    challenge_id=login_response.challenge_id, otp="000000"
                ),
                redis=fake_redis,
                user_agent="pytest",
                ip_address="203.0.113.40",
            )
        assert exc.value.detail == "Invalid security code."

    with pytest.raises(HTTPException) as lock_exc:
        await verify_two_factor(
            db=db_session,
            settings=settings_env,
            request=TwoFAVerifyRequest(
                challenge_id=login_response.challenge_id,
                otp=pyotp.TOTP(secret).now(),
                captchaToken="token",
            ),
            redis=fake_redis,
            user_agent="pytest",
            ip_address="203.0.113.40",
        )
    assert lock_exc.value.status_code == status.HTTP_423_LOCKED


@pytest.mark.asyncio
async def test_logout_and_sign_out_others(
    db_session: Session, settings_env, fake_redis
):
    user = _create_user(
        db_session, email="grace@example.com", password="LogoutSecret!99"
    )

    first = await login_user(
        db=db_session,
        settings=settings_env,
        request=LoginRequest(email="grace@example.com", password="LogoutSecret!99"),
        redis=fake_redis,
        user_agent="agent-one",
        ip_address="203.0.113.55",
    )
    second = await login_user(
        db=db_session,
        settings=settings_env,
        request=LoginRequest(email="grace@example.com", password="LogoutSecret!99"),
        redis=fake_redis,
        user_agent="agent-two",
        ip_address="203.0.113.56",
    )

    sessions = db_session.execute(select(SessionModel)).scalars().all()
    active_session = next(s for s in sessions if s.user_agent == "agent-two")
    revoked_count = await sign_out_other_sessions(
        db=db_session, user=user, active_session=active_session
    )
    assert revoked_count >= 1
    db_session.refresh(active_session)
    assert active_session.revoked_at is None
    assert any(
        s.user_agent == "agent-one" and s.revoked_at is not None
        for s in db_session.execute(select(SessionModel)).scalars()
    )

    await logout_session(
        db=db_session,
        token=second.refresh_token,
        user_agent="agent-two",
        ip_address="203.0.113.56",
    )
    with pytest.raises(HTTPException):
        await refresh_tokens(
            db=db_session,
            settings=settings_env,
            request=RefreshRequest(refresh_token=second.refresh_token),
            redis=fake_redis,
            user_agent="agent-two",
            ip_address="203.0.113.56",
        )


def _get_recovery_codes(user: User) -> list[str]:
    if not user.recovery_codes:
        return []
    encryption = get_encryption_service()
    return encryption.decrypt_json(user.recovery_codes)
