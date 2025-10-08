"""Billing service for Stripe payment integration."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

import stripe
import structlog
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.db.models import PaymentTransaction, SubscriptionPlan, User, UserSubscription

logger = structlog.get_logger(__name__)
settings = get_settings()

# Initialize Stripe
stripe.api_key = settings.stripe_api_key


def create_stripe_customer(db: Session, user: User) -> str:
    """Create a Stripe customer for a user.

    Args:
        db: Database session
        user: User object

    Returns:
        Stripe customer ID
    """
    try:
        customer = stripe.Customer.create(
            email=user.email,
            name=f"{user.email}",
            metadata={
                "user_id": str(user.id),
            }
        )

        logger.info("stripe.customer.created", user_id=str(user.id), customer_id=customer.id)
        return customer.id

    except stripe.error.StripeError as e:
        logger.error("stripe.customer.create_failed", user_id=str(user.id), error=str(e))
        raise


def create_checkout_session(
    db: Session,
    user: User,
    plan: SubscriptionPlan,
    success_url: str,
    cancel_url: str,
) -> dict:
    """Create a Stripe Checkout session for subscription payment.

    Args:
        db: Database session
        user: User object
        plan: Subscription plan
        success_url: URL to redirect on success
        cancel_url: URL to redirect on cancel

    Returns:
        Dictionary with checkout session details
    """
    try:
        # Get or create Stripe customer
        subscription = db.query(UserSubscription).filter(
            UserSubscription.user_id == user.id
        ).order_by(UserSubscription.created_at.desc()).first()

        if subscription and subscription.stripe_customer_id:
            customer_id = subscription.stripe_customer_id
        else:
            customer_id = create_stripe_customer(db, user)

        # Create checkout session
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            line_items=[
                {
                    'price_data': {
                        'currency': 'usd',
                        'unit_amount': plan.price_cents,
                        'recurring': {
                            'interval': 'month',
                        },
                        'product_data': {
                            'name': plan.display_name,
                            'description': plan.description or '',
                        },
                    },
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'user_id': str(user.id),
                'plan_id': str(plan.id),
            },
        )

        logger.info(
            "stripe.checkout.created",
            user_id=str(user.id),
            plan=plan.name,
            session_id=session.id
        )

        return {
            'session_id': session.id,
            'url': session.url,
        }

    except stripe.error.StripeError as e:
        logger.error("stripe.checkout.create_failed", user_id=str(user.id), error=str(e))
        raise


def create_payment_intent(
    db: Session,
    user: User,
    amount_cents: int,
    currency: str = "usd",
    description: Optional[str] = None,
) -> dict:
    """Create a Stripe Payment Intent for one-time payment.

    Args:
        db: Database session
        user: User object
        amount_cents: Amount in cents
        currency: Currency code (default: usd)
        description: Payment description

    Returns:
        Dictionary with payment intent details
    """
    try:
        # Get or create Stripe customer
        subscription = db.query(UserSubscription).filter(
            UserSubscription.user_id == user.id
        ).order_by(UserSubscription.created_at.desc()).first()

        if subscription and subscription.stripe_customer_id:
            customer_id = subscription.stripe_customer_id
        else:
            customer_id = create_stripe_customer(db, user)

        # Create payment intent
        intent = stripe.PaymentIntent.create(
            customer=customer_id,
            amount=amount_cents,
            currency=currency,
            description=description,
            metadata={
                'user_id': str(user.id),
            },
        )

        logger.info(
            "stripe.payment_intent.created",
            user_id=str(user.id),
            amount_cents=amount_cents,
            intent_id=intent.id
        )

        return {
            'client_secret': intent.client_secret,
            'payment_intent_id': intent.id,
        }

    except stripe.error.StripeError as e:
        logger.error("stripe.payment_intent.create_failed", user_id=str(user.id), error=str(e))
        raise


def record_payment_transaction(
    db: Session,
    user_id: UUID,
    stripe_payment_intent_id: str,
    amount_cents: int,
    currency: str,
    status: str,
    subscription_id: Optional[UUID] = None,
    stripe_charge_id: Optional[str] = None,
    stripe_customer_id: Optional[str] = None,
    payment_method: Optional[str] = None,
    payment_method_last4: Optional[str] = None,
    description: Optional[str] = None,
) -> PaymentTransaction:
    """Record a payment transaction in the database.

    Args:
        db: Database session
        user_id: User ID
        stripe_payment_intent_id: Stripe Payment Intent ID
        amount_cents: Amount in cents
        currency: Currency code
        status: Payment status (succeeded, pending, failed)
        subscription_id: Optional subscription ID
        stripe_charge_id: Optional Stripe charge ID
        stripe_customer_id: Optional Stripe customer ID
        payment_method: Payment method type
        payment_method_last4: Last 4 digits of payment method
        description: Payment description

    Returns:
        PaymentTransaction object
    """
    transaction = PaymentTransaction(
        user_id=user_id,
        subscription_id=subscription_id,
        stripe_payment_intent_id=stripe_payment_intent_id,
        stripe_charge_id=stripe_charge_id,
        stripe_customer_id=stripe_customer_id,
        amount_cents=amount_cents,
        currency=currency,
        status=status,
        payment_method=payment_method,
        payment_method_last4=payment_method_last4,
        description=description,
        paid_at=datetime.utcnow() if status == "succeeded" else None,
    )

    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    logger.info(
        "payment.transaction.recorded",
        user_id=str(user_id),
        transaction_id=str(transaction.id),
        status=status,
        amount_cents=amount_cents
    )

    return transaction


def get_user_payment_history(
    db: Session,
    user_id: UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[PaymentTransaction]:
    """Get payment history for a user.

    Args:
        db: Database session
        user_id: User ID
        limit: Maximum number of records to return
        offset: Number of records to skip

    Returns:
        List of PaymentTransaction objects
    """
    return (
        db.query(PaymentTransaction)
        .filter(PaymentTransaction.user_id == user_id)
        .order_by(PaymentTransaction.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


__all__ = [
    "create_stripe_customer",
    "create_checkout_session",
    "create_payment_intent",
    "record_payment_transaction",
    "get_user_payment_history",
]
