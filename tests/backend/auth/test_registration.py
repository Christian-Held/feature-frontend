from __future__ import annotations

from datetime import datetime, timedelta, timezone
from importlib import reload
from typing import Any

import pytest
import pytest_asyncio
from fastapi import HTTPException
from fakeredis import aioredis
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend.auth.schemas.registration import (
    RegistrationRequest,
    ResendVerificationRequest,
)
from backend.auth.service.captcha import verify_turnstile
from backend.db.base import Base
from backend.db.models.user import EmailVerification, User, UserStatus
from backend.security.passwords import get_password_service


@pytest.fixture
def db_session(settings_env) -> Session:
    """Provide an isolated in-memory SQLite session for each test."""

    from sqlalchemy import create_engine

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, future=True)
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


@pytest.fixture
def registration_service(settings_env):
    import backend.auth.email.tasks as email_tasks
    import backend.auth.service.registration_service as service

    reload(email_tasks)
    reload(service)
    return service


@pytest.fixture
def email_outbox(monkeypatch, registration_service):
    sent: list[dict[str, Any]] = []

    def _capture(email: str, url: str) -> None:
        sent.append({"email": email, "url": url})

    monkeypatch.setattr(registration_service, "enqueue_verification_email", _capture)
    return sent


@pytest.fixture(autouse=True)
def stub_captcha(monkeypatch, registration_service):
    async def _noop(**kwargs):
        return None

    monkeypatch.setattr(registration_service, "verify_turnstile", _noop)


@pytest.mark.asyncio
async def test_turnstile_success(settings_env):
    class DummyResponse:
        def __init__(self, data: dict[str, Any]):
            self._data = data

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return self._data

    class DummyClient:
        async def post(self, url: str, data: dict[str, Any]):
            assert data["secret"] == settings_env.turnstile_secret_key
            return DummyResponse({"success": True})

    await verify_turnstile(captcha_token="token", settings=settings_env, http_client=DummyClient())


@pytest.mark.asyncio
async def test_turnstile_failure(settings_env):
    class DummyResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {"success": False, "error-codes": ["invalid-input-response"]}

    class DummyClient:
        async def post(self, url: str, data: dict[str, Any]):
            return DummyResponse()

    with pytest.raises(HTTPException) as exc:
        await verify_turnstile(captcha_token="bad", settings=settings_env, http_client=DummyClient())
    assert exc.value.status_code == 400
    assert "Captcha" in exc.value.detail


@pytest.mark.asyncio
async def test_register_new_user(db_session: Session, settings_env, fake_redis, email_outbox, registration_service):
    request = RegistrationRequest(email="alice@example.com", password="SuperSecret!23", captchaToken="token")

    message = await registration_service.register_user(
        session=db_session,
        request=request,
        settings=settings_env,
        remote_ip="203.0.113.10",
        redis=fake_redis,
    )

    assert "Registrierung fast abgeschlossen" in message
    assert len(email_outbox) == 1

    user = db_session.execute(select(User)).scalar_one()
    assert user.status == UserStatus.UNVERIFIED
    assert user.email == "alice@example.com"
    assert get_password_service().verify(user.password_hash, "SuperSecret!23")

    verification = db_session.execute(select(EmailVerification)).scalar_one()
    token = email_outbox[0]["url"].split("token=")[1]
    assert token.split(".")[0] == str(verification.id)


@pytest.mark.asyncio
async def test_register_existing_verified_conflict(db_session: Session, settings_env, fake_redis, email_outbox, registration_service):
    password_hash = get_password_service().hash("ExistingSecret!45")
    user = User(
        email="bob@example.com",
        status=UserStatus.ACTIVE,
        email_verified_at=datetime.now(timezone.utc),
        password_hash=password_hash,
    )
    db_session.add(user)
    db_session.commit()

    request = RegistrationRequest(email="bob@example.com", password="AnotherSecret!56", captchaToken="token")

    with pytest.raises(HTTPException) as exc:
        await registration_service.register_user(
            session=db_session,
            request=request,
            settings=settings_env,
            remote_ip="198.51.100.7",
            redis=fake_redis,
        )
    assert exc.value.status_code == 409
    assert exc.value.detail == "Email already registered"
    assert len(email_outbox) == 0


@pytest.mark.asyncio
async def test_register_resends_existing_token(db_session: Session, settings_env, fake_redis, email_outbox, registration_service):
    request = RegistrationRequest(email="carol@example.com", password="Password!234", captchaToken="token")
    await registration_service.register_user(
        session=db_session,
        request=request,
        settings=settings_env,
        remote_ip="203.0.113.11",
        redis=fake_redis,
    )

    first_token = email_outbox[0]["url"].split("token=")[1]

    await registration_service.register_user(
        session=db_session,
        request=request,
        settings=settings_env,
        remote_ip="203.0.113.11",
        redis=fake_redis,
    )

    assert len(email_outbox) == 2
    second_token = email_outbox[1]["url"].split("token=")[1]
    assert first_token == second_token

    count = db_session.execute(select(EmailVerification)).scalars().all()
    assert len(count) == 1


@pytest.mark.asyncio
async def test_register_with_expired_token_creates_new(db_session: Session, settings_env, fake_redis, email_outbox, registration_service):
    request = RegistrationRequest(email="dave@example.com", password="Password!234", captchaToken="token")
    await registration_service.register_user(
        session=db_session,
        request=request,
        settings=settings_env,
        remote_ip="192.0.2.1",
        redis=fake_redis,
    )

    verification = db_session.execute(select(EmailVerification)).scalar_one()
    verification.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.flush()

    await registration_service.register_user(
        session=db_session,
        request=RegistrationRequest(email="dave@example.com", password="NewSecret!345", captchaToken="token"),
        settings=settings_env,
        remote_ip="192.0.2.1",
        redis=fake_redis,
    )

    assert len(email_outbox) == 2
    first_token = email_outbox[0]["url"].split("token=")[1]
    second_token = email_outbox[1]["url"].split("token=")[1]
    assert first_token != second_token

    verifications = db_session.execute(select(EmailVerification)).scalars().all()
    assert len(verifications) == 1
    user = db_session.execute(select(User)).scalar_one()
    assert get_password_service().verify(user.password_hash, "NewSecret!345")


@pytest.mark.asyncio
async def test_resend_rate_limit(db_session: Session, settings_env, fake_redis, email_outbox, registration_service):
    request = RegistrationRequest(email="erin@example.com", password="Password!234", captchaToken="token")
    await registration_service.register_user(
        session=db_session,
        request=request,
        settings=settings_env,
        remote_ip="192.0.2.3",
        redis=fake_redis,
    )

    resend_request = ResendVerificationRequest(email="erin@example.com")
    for _ in range(3):
        await registration_service.resend_verification(
            session=db_session,
            request=resend_request,
            settings=settings_env,
            redis=fake_redis,
        )

    with pytest.raises(HTTPException) as exc:
        await registration_service.resend_verification(
            session=db_session,
            request=resend_request,
            settings=settings_env,
            redis=fake_redis,
        )
    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_complete_email_verification_success(db_session: Session, settings_env, fake_redis, email_outbox, registration_service):
    request = RegistrationRequest(email="frank@example.com", password="Password!234", captchaToken="token")
    await registration_service.register_user(
        session=db_session,
        request=request,
        settings=settings_env,
        remote_ip="192.0.2.4",
        redis=fake_redis,
    )

    url = email_outbox[-1]["url"]
    token = url.split("token=")[1]

    user, verification, _ = await registration_service.complete_email_verification(
        session=db_session,
        token=token,
        settings=settings_env,
    )

    assert user.status == UserStatus.ACTIVE
    assert user.email_verified_at is not None
    assert verification.used_at is not None
    assert db_session.execute(select(EmailVerification)).scalars().all() == []


@pytest.mark.asyncio
async def test_complete_email_verification_expired(db_session: Session, settings_env, fake_redis, email_outbox, registration_service):
    request = RegistrationRequest(email="gina@example.com", password="Password!234", captchaToken="token")
    await registration_service.register_user(
        session=db_session,
        request=request,
        settings=settings_env,
        remote_ip="192.0.2.5",
        redis=fake_redis,
    )

    verification = db_session.execute(select(EmailVerification)).scalar_one()
    verification.expires_at = datetime.now(timezone.utc) - timedelta(hours=2)
    db_session.flush()
    token = email_outbox[-1]["url"].split("token=")[1]

    with pytest.raises(HTTPException) as exc:
        await registration_service.complete_email_verification(
            session=db_session,
            token=token,
            settings=settings_env,
        )
    assert exc.value.status_code == 400

    user = db_session.execute(select(User)).scalar_one()
    assert user.status == UserStatus.UNVERIFIED
    assert user.email_verified_at is None
    assert db_session.execute(select(EmailVerification)).scalars().all() == []
