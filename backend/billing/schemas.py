"""Pydantic schemas for billing API."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CheckoutSessionCreate(BaseModel):
    """Request to create a checkout session."""

    plan_id: UUID
    success_url: str = Field(..., description="URL to redirect on successful payment")
    cancel_url: str = Field(..., description="URL to redirect on cancelled payment")


class CheckoutSessionResponse(BaseModel):
    """Response with checkout session details."""

    session_id: str
    url: str


class PaymentIntentCreate(BaseModel):
    """Request to create a payment intent."""

    amount_cents: int = Field(..., gt=0, description="Amount in cents")
    currency: str = Field(default="usd", max_length=3, description="Currency code")
    description: Optional[str] = Field(None, description="Payment description")


class PaymentIntentResponse(BaseModel):
    """Response with payment intent details."""

    client_secret: str
    payment_intent_id: str


class PaymentTransactionSchema(BaseModel):
    """Payment transaction schema."""

    id: UUID
    user_id: UUID
    subscription_id: Optional[UUID]

    stripe_payment_intent_id: Optional[str]
    stripe_charge_id: Optional[str]
    stripe_customer_id: Optional[str]

    amount_cents: int
    currency: str
    status: str

    payment_method: Optional[str]
    payment_method_last4: Optional[str]

    description: Optional[str]
    failure_reason: Optional[str]

    paid_at: Optional[datetime]
    refunded_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @property
    def amount_decimal(self) -> Decimal:
        """Return amount as decimal dollars."""
        return Decimal(self.amount_cents) / 100


class PaymentHistoryResponse(BaseModel):
    """Response for payment history."""

    transactions: list[PaymentTransactionSchema]
    total: int


class StripePublishableKeyResponse(BaseModel):
    """Response with Stripe publishable key."""

    publishable_key: str


__all__ = [
    "CheckoutSessionCreate",
    "CheckoutSessionResponse",
    "PaymentIntentCreate",
    "PaymentIntentResponse",
    "PaymentTransactionSchema",
    "PaymentHistoryResponse",
    "StripePublishableKeyResponse",
]
