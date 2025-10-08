"""Rate limit information API for subscription users."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth.api.deps import require_current_user
from backend.db.models.user import User
from backend.db.session import get_db
from backend.subscription import service

router = APIRouter(prefix="/v1/subscription", tags=["subscription"])


class RateLimitInfo(BaseModel):
    """Rate limit information for the current user."""

    base_limit: int
    multiplier: float
    effective_limit: int
    plan_name: str


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
