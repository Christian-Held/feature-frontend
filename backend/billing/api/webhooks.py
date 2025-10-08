"""Stripe webhook handlers."""

from __future__ import annotations

import stripe
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.billing import service
from backend.core.config import get_settings
from backend.db.models import UserSubscription
from backend.db.session import get_db

router = APIRouter(prefix="/v1/webhooks", tags=["webhooks"])
logger = structlog.get_logger(__name__)
settings = get_settings()


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """Handle Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError:
        logger.error("stripe.webhook.invalid_payload")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        logger.error("stripe.webhook.invalid_signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle the event
    event_type = event['type']
    event_data = event['data']['object']

    logger.info("stripe.webhook.received", event_type=event_type)

    # Handle payment intent succeeded
    if event_type == 'payment_intent.succeeded':
        payment_intent = event_data

        # Record the payment transaction
        user_id = payment_intent.get('metadata', {}).get('user_id')
        if user_id:
            service.record_payment_transaction(
                db=db,
                user_id=user_id,
                stripe_payment_intent_id=payment_intent['id'],
                amount_cents=payment_intent['amount'],
                currency=payment_intent['currency'],
                status='succeeded',
                stripe_charge_id=payment_intent.get('latest_charge'),
                stripe_customer_id=payment_intent.get('customer'),
                payment_method=payment_intent.get('payment_method_types', [''])[0],
                description=payment_intent.get('description'),
            )

    # Handle checkout session completed
    elif event_type == 'checkout.session.completed':
        session = event_data

        user_id = session.get('metadata', {}).get('user_id')
        plan_id = session.get('metadata', {}).get('plan_id')

        if user_id and plan_id:
            # Update user subscription
            subscription = db.query(UserSubscription).filter(
                UserSubscription.user_id == user_id
            ).order_by(UserSubscription.created_at.desc()).first()

            if subscription:
                subscription.stripe_subscription_id = session.get('subscription')
                subscription.stripe_customer_id = session.get('customer')
                subscription.status = 'active'
                db.commit()

                logger.info(
                    "stripe.checkout.completed",
                    user_id=user_id,
                    plan_id=plan_id,
                    subscription_id=session.get('subscription')
                )

    # Handle subscription deleted
    elif event_type == 'customer.subscription.deleted':
        subscription_data = event_data

        # Find and update subscription
        subscription = db.query(UserSubscription).filter(
            UserSubscription.stripe_subscription_id == subscription_data['id']
        ).first()

        if subscription:
            subscription.status = 'cancelled'
            db.commit()

            logger.info(
                "stripe.subscription.cancelled",
                subscription_id=subscription_data['id']
            )

    # Handle subscription updated
    elif event_type == 'customer.subscription.updated':
        subscription_data = event_data

        # Find and update subscription
        subscription = db.query(UserSubscription).filter(
            UserSubscription.stripe_subscription_id == subscription_data['id']
        ).first()

        if subscription:
            subscription.status = subscription_data['status']
            db.commit()

            logger.info(
                "stripe.subscription.updated",
                subscription_id=subscription_data['id'],
                status=subscription_data['status']
            )

    # Handle payment failed
    elif event_type == 'payment_intent.payment_failed':
        payment_intent = event_data

        user_id = payment_intent.get('metadata', {}).get('user_id')
        if user_id:
            service.record_payment_transaction(
                db=db,
                user_id=user_id,
                stripe_payment_intent_id=payment_intent['id'],
                amount_cents=payment_intent['amount'],
                currency=payment_intent['currency'],
                status='failed',
                stripe_customer_id=payment_intent.get('customer'),
                failure_reason=payment_intent.get('last_payment_error', {}).get('message'),
            )

    return {"status": "success"}


__all__ = ["router"]
