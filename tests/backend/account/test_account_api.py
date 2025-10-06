import asyncio
import os
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import asyncio
import os
from decimal import Decimal
from pathlib import Path

import fakeredis.aioredis
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/testdb")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_ACTIVE_KID", "current")
os.environ.setdefault("JWT_PRIVATE_KEYS_DIR", str(Path(__file__).resolve().parent))
os.environ.setdefault("TURNSTILE_SECRET_KEY", "test-key")
os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("EMAIL_FROM_ADDRESS", "noreply@example.com")
os.environ.setdefault("FRONTEND_BASE_URL", "https://frontend.example.com")
os.environ.setdefault("API_BASE_URL", "https://api.example.com")
os.environ.setdefault("EMAIL_VERIFICATION_SECRET", "secret")
os.environ.setdefault("ADMIN_EMAIL", "admin@example.com")
os.environ.setdefault("ADMIN_PASSWORD", "password123!")

from backend.account.api import router as account_router
from backend.account.dependencies import get_redis
from backend.account.services import SpendAccountingService
from backend.auth.api.deps import require_current_user
from backend.core.config import get_settings
from backend.db.base import Base
from backend.db.models.billing import Plan
from backend.db.models.user import User, UserStatus
from backend.db.session import get_db


@pytest.fixture
def account_app(settings_env):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, expire_on_commit=False, future=True, class_=Session)
    session = TestingSession()

    fake_redis = fakeredis.aioredis.FakeRedis()

    user = User(
        id=uuid4(),
        email="user@example.com",
        status=UserStatus.ACTIVE,
        password_hash="hash",
    )
    plan_free = Plan(id=uuid4(), code="FREE", name="Free", monthly_price_usd=Decimal("0.00"))
    plan_pro = Plan(id=uuid4(), code="PRO", name="Pro", monthly_price_usd=Decimal("99.00"))
    session.add_all([user, plan_free, plan_pro])
    session.commit()

    app = FastAPI()
    app.include_router(account_router)

    async def override_get_redis():
        return fake_redis

    def override_get_db():
        yield session

    async def override_current_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_current_user] = override_current_user
    app.dependency_overrides[get_settings] = lambda: settings_env
    app.dependency_overrides[get_redis] = override_get_redis

    client = TestClient(app)

    yield client, session, user, fake_redis

    client.close()
    session.close()
    Base.metadata.drop_all(bind=engine)
    asyncio.run(fake_redis.aclose())


def test_plan_and_limits_flow(account_app):
    client, session, user, _ = account_app

    response = client.get("/v1/account/plan")
    assert response.status_code == 200
    data = response.json()
    assert data["plan"] == "FREE"

    response = client.post("/v1/account/plan", json={"plan": "PRO"})
    assert response.status_code == 200
    assert response.json()["plan"] == "PRO"

    response = client.post("/v1/account/limits", json={"monthly_cap_usd": "250.00", "hard_stop": False})
    assert response.status_code == 200

    response = client.get("/v1/account/limits")
    assert response.status_code == 200
    limits = response.json()
    assert limits["monthly_cap_usd"] == "250.00"
    assert limits["hard_stop"] is False
    assert limits["usage_usd"] == "0.00"
    assert limits["remaining_usd"] == "250.00"


def test_warning_header_emitted(account_app):
    client, session, user, _ = account_app

    client.post("/v1/account/limits", json={"monthly_cap_usd": "10.00", "hard_stop": False})
    accounting = SpendAccountingService(session)
    accounting.record(user.id, Decimal("10.00"), meta={"reason": "usage"})
    session.commit()

    response = client.get("/v1/account/limits")
    assert response.headers.get("X-Spend-Warning") == "cap_reached"
    body = response.json()
    assert body["cap_reached"] is True
    assert body["remaining_usd"] == "0.00"


def test_rate_limit_enforced(account_app):
    client, _, __, fake_redis = account_app

    for _ in range(5):
        assert client.post("/v1/account/plan", json={"plan": "PRO"}).status_code == 200

    response = client.post("/v1/account/plan", json={"plan": "PRO"})
    assert response.status_code == 429
    assert response.json()["detail"] == "Rate limit exceeded. Please try again later."

    asyncio.run(fake_redis.flushall())

    for _ in range(10):
        assert client.post("/v1/account/limits", json={"monthly_cap_usd": "50.00", "hard_stop": False}).status_code == 200

    response = client.post("/v1/account/limits", json={"monthly_cap_usd": "50.00", "hard_stop": False})
    assert response.status_code == 429
    assert response.json()["detail"] == "Rate limit exceeded. Please try again later."
