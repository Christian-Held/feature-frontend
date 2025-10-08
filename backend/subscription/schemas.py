"""Pydantic schemas for subscription API."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class SubscriptionPlanSchema(BaseModel):
    """Subscription plan schema."""

    id: UUID
    name: str
    display_name: str
    description: str | None
    price_cents: int
    billing_period: str | None
    features: dict[str, Any]
    rate_limit_multiplier: Decimal
    max_jobs_per_month: int | None
    max_storage_mb: int | None
    max_api_calls_per_day: int | None
    is_active: bool

    class Config:
        from_attributes = True


class UserSubscriptionSchema(BaseModel):
    """User subscription schema."""

    id: UUID
    user_id: UUID
    plan_id: UUID
    status: str
    started_at: datetime
    expires_at: datetime | None
    cancelled_at: datetime | None
    current_period_start: datetime | None
    current_period_end: datetime | None

    class Config:
        from_attributes = True


class UserUsageSchema(BaseModel):
    """User usage schema."""

    period_start: datetime
    period_end: datetime
    api_calls: int
    jobs_created: int
    storage_used_mb: int
    compute_minutes: int

    class Config:
        from_attributes = True


class SubscriptionResponse(BaseModel):
    """Response for GET /v1/subscription/me."""

    subscription: UserSubscriptionSchema | None
    plan: SubscriptionPlanSchema


class QuotaLimitsSchema(BaseModel):
    """Quota limits schema."""

    jobs: int | None = Field(description="Max jobs per month, None = unlimited")
    storage: int | None = Field(description="Max storage in MB, None = unlimited")
    api_calls: int | None = Field(description="Max API calls per day, None = unlimited")


class UsageResponse(BaseModel):
    """Response for GET /v1/subscription/usage."""

    usage: UserUsageSchema | None
    limits: QuotaLimitsSchema


class PlanListResponse(BaseModel):
    """Response for GET /v1/subscription/plans."""

    plans: list[SubscriptionPlanSchema]


class RateLimitInfo(BaseModel):
    """Rate limit information for the current user."""

    base_limit: int
    multiplier: float
    effective_limit: int
    plan_name: str


__all__ = [
    "SubscriptionPlanSchema",
    "UserSubscriptionSchema",
    "UserUsageSchema",
    "SubscriptionResponse",
    "UsageResponse",
    "PlanListResponse",
    "QuotaLimitsSchema",
    "RateLimitInfo",
]
