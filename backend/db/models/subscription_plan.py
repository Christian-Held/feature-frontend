"""Subscription plan model."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from backend.db.base import Base


class SubscriptionPlan(Base):
    """Subscription plan model (free, pro, enterprise)."""

    __tablename__ = "subscription_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True, index=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price_cents = Column(Integer, nullable=False, default=0)
    billing_period = Column(String(20), nullable=True)  # 'monthly', 'yearly', null for free

    # Feature flags stored as JSON
    features = Column(JSONB, nullable=False, default=dict)

    # Limits & Quotas
    rate_limit_multiplier = Column(Numeric(4, 2), default=Decimal("1.0"))
    max_jobs_per_month = Column(Integer, nullable=True)  # NULL = unlimited
    max_storage_mb = Column(Integer, nullable=True)
    max_api_calls_per_day = Column(Integer, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    subscriptions = relationship("UserSubscription", back_populates="plan")

    def __repr__(self):
        return f"<SubscriptionPlan(name='{self.name}', price={self.price_cents})>"
