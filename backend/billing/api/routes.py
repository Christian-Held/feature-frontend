"""Billing API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.auth.api.deps import require_current_user
from backend.billing import service
from backend.billing.schemas import (
    CheckoutSessionCreate,
    CheckoutSessionResponse,
    PaymentHistoryResponse,
    PaymentIntentCreate,
    PaymentIntentResponse,
    StripePublishableKeyResponse,
)
from backend.core.config import get_settings
from backend.db.models import SubscriptionPlan, User
from backend.db.session import get_db

router = APIRouter(prefix="/v1/billing", tags=["billing"])
settings = get_settings()


@router.get("/config", response_model=StripePublishableKeyResponse)
def get_stripe_config():
    """Get Stripe publishable key for frontend."""
    return StripePublishableKeyResponse(
        publishable_key=settings.stripe_publishable_key
    )


@router.post("/checkout-session", response_model=CheckoutSessionResponse)
def create_checkout_session(
    data: CheckoutSessionCreate,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout session for subscription payment."""
    # Get the plan
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == data.plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if not plan.is_active:
        raise HTTPException(status_code=400, detail="Plan is not active")

    # Create checkout session
    try:
        session = service.create_checkout_session(
            db=db,
            user=current_user,
            plan=plan,
            success_url=data.success_url,
            cancel_url=data.cancel_url,
        )
        return CheckoutSessionResponse(**session)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create checkout session: {str(e)}")


@router.post("/payment-intent", response_model=PaymentIntentResponse)
def create_payment_intent(
    data: PaymentIntentCreate,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Payment Intent for one-time payment."""
    try:
        intent = service.create_payment_intent(
            db=db,
            user=current_user,
            amount_cents=data.amount_cents,
            currency=data.currency,
            description=data.description,
        )
        return PaymentIntentResponse(**intent)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create payment intent: {str(e)}")


@router.get("/history", response_model=PaymentHistoryResponse)
def get_payment_history(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    """Get payment history for the current user."""
    transactions = service.get_user_payment_history(
        db=db,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )

    # Get total count
    from backend.db.models import PaymentTransaction
    total = db.query(PaymentTransaction).filter(
        PaymentTransaction.user_id == current_user.id
    ).count()

    return PaymentHistoryResponse(
        transactions=transactions,
        total=total,
    )


__all__ = ["router"]
