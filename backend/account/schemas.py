"""Pydantic schemas for account plan and spend limit APIs."""

from __future__ import annotations

from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class PlanCode(str, Enum):
    """Supported subscription plans."""

    FREE = "FREE"
    PRO = "PRO"


class PlanResponse(BaseModel):
    """Response payload describing the active plan for a user."""

    plan: PlanCode
    name: str
    monthly_price_usd: Decimal = Field(..., ge=Decimal("0"))


class PlanUpdateRequest(BaseModel):
    """Request payload to update the active plan."""

    plan: PlanCode


class SpendLimitResponse(BaseModel):
    """Response payload describing the current spend limit state."""

    monthly_cap_usd: Decimal = Field(..., ge=Decimal("0"))
    hard_stop: bool
    usage_usd: Decimal = Field(..., ge=Decimal("0"))
    remaining_usd: Decimal = Field(..., ge=Decimal("0"))
    cap_reached: bool


class SpendLimitUpdateRequest(BaseModel):
    """Request payload to update spend limits."""

    monthly_cap_usd: Decimal = Field(..., ge=Decimal("0"))
    hard_stop: bool


class SpendTotals(BaseModel):
    """Aggregate spend totals for the current UTC month."""

    usage_usd: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    cap_usd: Decimal | None = Field(default=None, ge=Decimal("0"))
    remaining_usd: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    cap_reached: bool = False
    hard_stop: bool = False


__all__ = [
    "PlanCode",
    "PlanResponse",
    "PlanUpdateRequest",
    "SpendLimitResponse",
    "SpendLimitUpdateRequest",
    "SpendTotals",
]
