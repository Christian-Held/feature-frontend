"""Subscription API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.auth.api.deps import require_current_user
from backend.db.models import SubscriptionPlan, User
from backend.db.session import get_db
from backend.subscription import service
from backend.subscription.schemas import (
    PlanListResponse,
    QuotaLimitsSchema,
    RateLimitInfo,
    SubscriptionResponse,
    UsageResponse,
)

router = APIRouter(prefix="/v1/subscription", tags=["subscription"])


@router.get("/me", response_model=SubscriptionResponse)
def get_my_subscription(
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    """Get current user's subscription and plan."""
    subscription = service.get_user_subscription(db, current_user.id)
    plan = service.get_user_plan(db, current_user.id)

    return SubscriptionResponse(
        subscription=subscription,
        plan=plan,
    )


@router.get("/usage", response_model=UsageResponse)
def get_my_usage(
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    """Get current period usage and limits."""
    usage = service.get_current_period_usage(db, current_user.id)
    plan = service.get_user_plan(db, current_user.id)

    return UsageResponse(
        usage=usage,
        limits=QuotaLimitsSchema(
            jobs=plan.max_jobs_per_month,
            storage=plan.max_storage_mb,
            api_calls=plan.max_api_calls_per_day,
        ),
    )


@router.get("/plans", response_model=PlanListResponse)
def list_plans(db: Session = Depends(get_db)):
    """List all available subscription plans."""
    plans = db.query(SubscriptionPlan).filter(SubscriptionPlan.is_active == True).all()

    return PlanListResponse(plans=plans)


@router.get("/rate-limits", response_model=RateLimitInfo)
def get_my_rate_limits(
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
) -> RateLimitInfo:
    """Get the current user's rate limit multiplier and effective limits.

    This endpoint returns information about how many requests per minute
    the user can make based on their subscription plan.
    """
    # Get user's plan
    plan = service.get_user_plan(db, current_user.id)

    # Base rate limit (from config, typically 100 req/min for free tier)
    base_limit = 100

    # Get multiplier from plan
    multiplier = float(plan.rate_limit_multiplier) if plan and plan.rate_limit_multiplier else 1.0

    # Calculate effective limit
    effective_limit = int(base_limit * multiplier)

    return RateLimitInfo(
        base_limit=base_limit,
        multiplier=multiplier,
        effective_limit=effective_limit,
        plan_name=plan.name if plan else "free",
    )


__all__ = ["router"]
