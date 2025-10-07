from __future__ import annotations

import asyncio
import base64
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import fakeredis.aioredis
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.scripts.jwk_generate import create_jwk

_current_jwk = create_jwk(kid="current-admin")
_next_jwk = create_jwk(kid="next-admin")
_previous_jwk = create_jwk(kid="prev-admin")
_encryption_keys = {
    "v1": base64.b64encode(b"1" * 32).decode("utf-8"),
    "v0": base64.b64encode(b"2" * 32).decode("utf-8"),
}

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/testdb"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_JWK_CURRENT", json.dumps(_current_jwk))
os.environ.setdefault("JWT_JWK_NEXT", json.dumps(_next_jwk))
os.environ.setdefault("JWT_JWK_PREVIOUS", json.dumps(_previous_jwk))
os.environ.setdefault("JWT_PREVIOUS_GRACE_SECONDS", "86400")
os.environ.setdefault("TURNSTILE_SECRET_KEY", "test-key")
os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("EMAIL_FROM_ADDRESS", "noreply@example.com")
os.environ.setdefault("FRONTEND_BASE_URL", "https://frontend.example.com")
os.environ.setdefault("API_BASE_URL", "https://api.example.com")
os.environ.setdefault("EMAIL_VERIFICATION_SECRET", "secret")
os.environ.setdefault("ADMIN_EMAIL", "admin@example.com")
os.environ.setdefault("ADMIN_PASSWORD", "password123!")
os.environ.setdefault("ENCRYPTION_KEYS", json.dumps(_encryption_keys))
os.environ.setdefault("ENCRYPTION_KEY_ACTIVE", "v1")
os.environ.setdefault("SMTP_HOST", "localhost")
os.environ.setdefault("SMTP_PORT", "1025")
os.environ.setdefault("SMTP_USE_TLS", "false")

from backend.admin.api import router as admin_router
from backend.admin.services import ALLOWED_ROLE_NAMES
from backend.auth.api.deps import require_current_user
from backend.core.config import get_settings
from backend.db.base import Base
from backend.db.models.audit import AuditLog
from backend.db.models.user import Role, User, UserStatus
from backend.db.session import get_db
from backend.middleware.request_context import RequestContextMiddleware
from backend.redis.client import get_redis_client
from backend.security.encryption import get_encryption_service


@pytest.fixture
def admin_app(settings_env):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(
        bind=engine, expire_on_commit=False, future=True, class_=Session
    )
    session = TestingSession()

    role_objects = {name: Role(name=name) for name in ALLOWED_ROLE_NAMES}
    session.add_all(role_objects.values())

    admin_user = User(
        id=uuid4(),
        email="admin@example.com",
        status=UserStatus.ACTIVE,
        email_verified_at=datetime.now(timezone.utc),
        password_hash="hash",
        mfa_enabled=True,
    )
    admin_user.roles.append(role_objects["ADMIN"])

    active_user = User(
        id=uuid4(),
        email="user@example.com",
        status=UserStatus.ACTIVE,
        email_verified_at=datetime.now(timezone.utc),
        password_hash="hash",
        mfa_enabled=False,
    )
    active_user.roles.append(role_objects["USER"])

    billing_user = User(
        id=uuid4(),
        email="billing@example.com",
        status=UserStatus.ACTIVE,
        email_verified_at=datetime.now(timezone.utc),
        password_hash="hash",
        mfa_enabled=False,
    )
    billing_user.roles.append(role_objects["BILLING_ADMIN"])

    unverified_user = User(
        id=uuid4(),
        email="pending@example.com",
        status=UserStatus.UNVERIFIED,
        password_hash="hash",
        mfa_enabled=False,
    )
    unverified_user.roles.append(role_objects["USER"])

    session.add_all([admin_user, active_user, billing_user, unverified_user])
    session.commit()

    fake_redis = fakeredis.aioredis.FakeRedis()

    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)
    app.include_router(admin_router)

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = lambda: settings_env
    app.dependency_overrides[get_redis_client] = lambda: fake_redis

    current_user_ref: dict[str, User] = {"user": admin_user}

    async def override_current_user():
        return current_user_ref["user"]

    app.dependency_overrides[require_current_user] = override_current_user

    client = TestClient(app)

    yield {
        "client": client,
        "session": session,
        "admin": admin_user,
        "active_user": active_user,
        "billing_user": billing_user,
        "unverified_user": unverified_user,
        "set_current_user": lambda user: current_user_ref.__setitem__("user", user),
        "redis": fake_redis,
    }

    client.close()
    session.close()
    Base.metadata.drop_all(bind=engine)
    asyncio.run(fake_redis.aclose())


def _flush(redis: fakeredis.aioredis.FakeRedis) -> None:
    asyncio.run(redis.flushall())


def test_rbac_requires_admin_role_and_mfa(admin_app):
    client = admin_app["client"]
    session = admin_app["session"]
    admin = admin_app["admin"]
    set_current_user = admin_app["set_current_user"]
    redis = admin_app["redis"]
    _flush(redis)

    admin.mfa_enabled = False
    session.commit()
    response = client.get("/v1/admin/users")
    assert response.status_code == 403
    assert (
        response.json()["detail"] == "You don’t have permission to perform this action."
    )

    admin.mfa_enabled = True
    session.commit()
    set_current_user(admin_app["active_user"])
    response = client.get("/v1/admin/users")
    assert response.status_code == 403
    assert (
        response.json()["detail"] == "You don’t have permission to perform this action."
    )

    set_current_user(admin)
    response = client.get("/v1/admin/users")
    assert response.status_code == 200


def test_list_users_filters_and_pagination(admin_app):
    client = admin_app["client"]
    redis = admin_app["redis"]
    _flush(redis)
    session = admin_app["session"]
    response = client.get("/v1/admin/users")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 4
    emails = [item["email"] for item in body["items"]]
    assert "admin@example.com" in emails

    response = client.get("/v1/admin/users", params={"status": "UNVERIFIED"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["email"] == "pending@example.com"

    response = client.get("/v1/admin/users", params={"role": "BILLING_ADMIN"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["email"] == "billing@example.com"

    response = client.get("/v1/admin/users", params={"q": "admin@"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["email"] == "admin@example.com"

    response = client.get("/v1/admin/users", params={"sort": "created_at_asc"})
    assert response.status_code == 200
    data = response.json()
    assert data["items"][0]["email"] == "admin@example.com"

    response = client.get("/v1/admin/users", params={"page": 2, "page_size": 2})
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 2
    assert len(data["items"]) == 2


def test_update_roles_emits_audit(admin_app):
    client = admin_app["client"]
    session = admin_app["session"]
    target = admin_app["active_user"]
    redis = admin_app["redis"]
    _flush(redis)

    response = client.post(
        f"/v1/admin/users/{target.id}/roles",
        json={"roles": ["SUPPORT", "BILLING_ADMIN"]},
    )
    assert response.status_code == 200
    payload = response.json()
    assert sorted(payload["roles"]) == ["BILLING_ADMIN", "SUPPORT"]

    refreshed = session.get(User, target.id)
    assert refreshed is not None
    assert sorted(role.name for role in refreshed.roles) == ["BILLING_ADMIN", "SUPPORT"]

    audit = (
        session.query(AuditLog).filter(AuditLog.action == "user_roles_changed").one()
    )
    assert audit.metadata_json["email_hash"]
    assert "@" not in audit.metadata_json["email_hash"]
    assert sorted(audit.metadata_json["roles"]) == ["BILLING_ADMIN", "SUPPORT"]


def test_lock_and_unlock_flow(admin_app):
    client = admin_app["client"]
    session = admin_app["session"]
    target = admin_app["active_user"]
    redis = admin_app["redis"]
    _flush(redis)

    response = client.post(f"/v1/admin/users/{target.id}/lock")
    assert response.status_code == 200
    session.refresh(target)
    assert target.status == UserStatus.DISABLED

    target.email_verified_at = datetime.now(timezone.utc)
    session.commit()
    response = client.post(f"/v1/admin/users/{target.id}/unlock")
    assert response.status_code == 200
    session.refresh(target)
    assert target.status == UserStatus.ACTIVE

    pending = admin_app["unverified_user"]
    response = client.post(f"/v1/admin/users/{pending.id}/unlock")
    assert response.status_code == 409
    assert response.json()["detail"] == "User must verify email before unlocking."


def test_reset_two_factor_clears_secrets(admin_app):
    client = admin_app["client"]
    session = admin_app["session"]
    target = admin_app["active_user"]
    redis = admin_app["redis"]
    _flush(redis)

    encryption = get_encryption_service()
    target.mfa_secret = encryption.encrypt_bytes(b"secret")
    target.recovery_codes = encryption.encrypt_json(["abc"])
    target.mfa_enabled = True
    session.commit()

    response = client.post(f"/v1/admin/users/{target.id}/reset-2fa")
    assert response.status_code == 200
    session.refresh(target)
    assert target.mfa_secret is None
    assert target.recovery_codes is None
    assert target.mfa_enabled is False


def test_resend_verification_rate_limit(admin_app, monkeypatch):
    client = admin_app["client"]
    target = admin_app["unverified_user"]
    redis = admin_app["redis"]
    _flush(redis)

    sent: list[str] = []

    def capture(email: str, verification_url: str):  # type: ignore[no-untyped-def]
        sent.append(verification_url)

    monkeypatch.setattr(
        "backend.auth.service.registration_service.enqueue_verification_email",
        capture,
    )

    for _ in range(3):
        response = client.post(f"/v1/admin/users/{target.id}/resend-verification")
        assert response.status_code == 200

    response = client.post(f"/v1/admin/users/{target.id}/resend-verification")
    assert response.status_code == 429
    assert response.json()["detail"] == "Rate limit exceeded. Please try again later."
    assert sent


def test_mutation_rate_limit_per_target(admin_app):
    client = admin_app["client"]
    target = admin_app["active_user"]
    redis = admin_app["redis"]
    _flush(redis)

    for _ in range(10):
        response = client.post(f"/v1/admin/users/{target.id}/reset-2fa")
        assert response.status_code == 200

    response = client.post(f"/v1/admin/users/{target.id}/reset-2fa")
    assert response.status_code == 429
    assert response.json()["detail"] == "Rate limit exceeded. Please try again later."


def test_audit_logs_listing_and_export(admin_app):
    client = admin_app["client"]
    redis = admin_app["redis"]
    target = admin_app["active_user"]
    _flush(redis)

    client.post(f"/v1/admin/users/{target.id}/lock")
    client.post(f"/v1/admin/users/{target.id}/unlock")

    response = client.get("/v1/admin/audit-logs")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2
    actions = {item["action"] for item in data["items"]}
    assert {"user_locked", "user_unlocked"}.issubset(actions)

    response = client.get("/v1/admin/audit-logs", params={"action": "user_locked"})
    assert response.status_code == 200
    filtered = response.json()
    assert all(item["action"] == "user_locked" for item in filtered["items"])

    export = client.get("/v1/admin/audit-logs/export", params={"format": "csv"})
    assert export.status_code == 200
    body = export.text
    assert "action" in body.splitlines()[0]
    assert "user_locked" in body
