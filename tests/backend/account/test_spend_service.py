import os
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from uuid import uuid4

import os
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
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

from backend.account.enforcement import CAP_BLOCK_MESSAGE, enforce_spend_cap
from backend.account.schemas import PlanCode
from backend.account.services import PlanService, SpendAccountingService, SpendLimitService
from backend.db.base import Base
from backend.db.models.audit import AuditLog
from backend.db.models.billing import Plan
from backend.db.models.user import User, UserStatus


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, expire_on_commit=False, future=True, class_=Session)
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def user(session: Session):
    usr = User(id=uuid4(), email="acct@example.com", status=UserStatus.ACTIVE, password_hash="hash")
    session.add(usr)
    plan_free = Plan(id=uuid4(), code="FREE", name="Free", monthly_price_usd=Decimal("0.00"))
    plan_pro = Plan(id=uuid4(), code="PRO", name="Pro", monthly_price_usd=Decimal("99.00"))
    session.add_all([plan_free, plan_pro])
    session.commit()
    return usr


def test_record_and_totals(session: Session, user: User):
    accounting = SpendAccountingService(session)
    limits = SpendLimitService(session)
    limits.update_limits(
        user_id=user.id,
        monthly_cap_usd=Decimal("50.00"),
        hard_stop=False,
        actor_user_id=user.id,
        ip=None,
        user_agent=None,
    )
    accounting.record(user.id, Decimal("10.25"), meta={"job_id": "job-1"})
    accounting.record(user.id, Decimal("5.75"), meta=None)
    session.commit()

    totals = accounting.get_month_totals(user.id)
    assert totals.usage_usd == Decimal("16.00")
    assert totals.remaining_usd == Decimal("34.00")
    assert totals.cap_reached is False


def test_enforce_spend_cap(session: Session, user: User):
    limits = SpendLimitService(session)
    limits.update_limits(
        user_id=user.id,
        monthly_cap_usd=Decimal("20.00"),
        hard_stop=True,
        actor_user_id=user.id,
        ip=None,
        user_agent=None,
    )
    accounting = SpendAccountingService(session)
    accounting.record(user.id, Decimal("20.00"), meta=None)
    session.commit()

    with pytest.raises(HTTPException) as exc:
        enforce_spend_cap(user.id, Decimal("1.00"), session=session)
    assert exc.value.status_code == 402
    assert exc.value.detail == CAP_BLOCK_MESSAGE

    limits.update_limits(
        user_id=user.id,
        monthly_cap_usd=Decimal("30.00"),
        hard_stop=False,
        actor_user_id=user.id,
        ip=None,
        user_agent=None,
    )
    session.commit()
    result = enforce_spend_cap(user.id, Decimal("15.00"), session=session, raise_on_block=False)
    assert result.cap_reached is True
    assert result.hard_stop is False
    assert result.warning_header == "cap_reached"


def test_audit_events_emitted(session: Session, user: User):
    plan_service = PlanService(session)
    limit_service = SpendLimitService(session)
    accounting = SpendAccountingService(session)

    plan_service.set_plan(
        user_id=user.id,
        plan_code=PlanCode.PRO,
        actor_user_id=user.id,
        ip="203.0.113.10",
        user_agent="pytest",
    )
    limit_service.update_limits(
        user_id=user.id,
        monthly_cap_usd=Decimal("100.00"),
        hard_stop=False,
        actor_user_id=user.id,
        ip="203.0.113.10",
        user_agent="pytest",
    )
    accounting.record(user.id, Decimal("42.00"), meta={"source": "unit-test"})
    accounting.enforce_cap(
        user_id=user.id,
        estimated_usd=Decimal("80.00"),
        actor_user_id=user.id,
        ip="203.0.113.10",
        user_agent="pytest",
    )
    session.commit()

    actions = {row.action for row in session.execute(select(AuditLog)).scalars()}
    assert {"plan_changed", "limits_changed", "spend_recorded", "cap_reached"}.issubset(actions)
