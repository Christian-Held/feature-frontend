"""Payment transaction model for tracking Stripe payments."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.db.base import Base


class PaymentTransaction(Base):
    """Payment transaction model for tracking all payment events."""

    __tablename__ = "payment_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("user_subscriptions.id", ondelete="SET NULL"), nullable=True)

    # Stripe IDs
    stripe_payment_intent_id = Column(String(255), nullable=True, unique=True, index=True)
    stripe_charge_id = Column(String(255), nullable=True)
    stripe_invoice_id = Column(String(255), nullable=True)
    stripe_customer_id = Column(String(255), nullable=True, index=True)

    # Payment details
    amount_cents = Column(Integer, nullable=False)  # Amount in cents
    currency = Column(String(3), nullable=False, default="usd")  # ISO currency code
    status = Column(String(50), nullable=False, index=True)  # succeeded, pending, failed, refunded

    # Payment method
    payment_method = Column(String(100), nullable=True)  # card, bank_transfer, etc.
    payment_method_last4 = Column(String(4), nullable=True)  # Last 4 digits of card

    # Metadata
    description = Column(Text, nullable=True)
    metadata_json = Column("metadata", Text, nullable=True)  # JSON string for extra data
    failure_reason = Column(Text, nullable=True)

    # Timestamps
    paid_at = Column(DateTime, nullable=True)
    refunded_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="payment_transactions")
    subscription = relationship("UserSubscription", back_populates="payment_transactions")

    def __repr__(self):
        return f"<PaymentTransaction(user_id={self.user_id}, amount={self.amount_cents / 100:.2f}, status='{self.status}')>"

    @property
    def amount_decimal(self) -> Decimal:
        """Return amount as decimal dollars."""
        return Decimal(self.amount_cents) / 100
