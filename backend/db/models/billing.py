"""Billing and plan related ORM models."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from backend.db.types import GUID


class PlanStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    CANCELED = "CANCELED"
    PAST_DUE = "PAST_DUE"


class Plan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Plan catalog metadata."""

    __tablename__ = "plans"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    monthly_price_usd: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, default=None)

    subscribers: Mapped[list["UserPlan"]] = relationship("UserPlan", back_populates="plan")


class UserPlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Plan enrollment state for a user."""

    __tablename__ = "user_plans"
    __table_args__ = (UniqueConstraint("user_id", "plan_id", name="uq_user_plans_user_plan"),)

    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plan_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("plans.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[PlanStatus] = mapped_column(Enum(PlanStatus, name="plan_status"), nullable=False, default=PlanStatus.ACTIVE)
    renews_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship("User", back_populates="plans")
    plan: Mapped["Plan"] = relationship("Plan", back_populates="subscribers")


class SpendLimit(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Monthly spend caps per user."""

    __tablename__ = "spend_limits"
    __table_args__ = (UniqueConstraint("user_id", name="uq_spend_limits_user"),)

    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    monthly_cap_usd: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    hard_stop: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


__all__ = ["Plan", "UserPlan", "SpendLimit", "PlanStatus"]

