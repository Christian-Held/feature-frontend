"""Subscription management service."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from backend.db.models import SubscriptionPlan, User, UserSubscription, UserUsage


def get_user_subscription(db: Session, user_id: UUID) -> UserSubscription | None:
    """Get active subscription for user."""
    return (
        db.query(UserSubscription)
        .filter(
            UserSubscription.user_id == user_id,
            UserSubscription.status == "active",
        )
        .first()
    )


def get_user_plan(db: Session, user_id: UUID) -> SubscriptionPlan:
    """Get subscription plan for user (defaults to free if no active subscription)."""
    subscription = get_user_subscription(db, user_id)
    if subscription and subscription.plan:
        return subscription.plan

    # Default to free plan
    free_plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == "free").first()
    if not free_plan:
        raise ValueError("Free plan not found in database. Run seed script.")
    return free_plan


def has_feature(db: Session, user_id: UUID, feature: str) -> bool:
    """Check if user has access to a specific feature."""
    plan = get_user_plan(db, user_id)
    return plan.features.get(feature, False)


def get_rate_limit_multiplier(db: Session, user_id: UUID) -> float:
    """Get rate limit multiplier for user's plan."""
    plan = get_user_plan(db, user_id)
    multiplier = plan.rate_limit_multiplier
    if multiplier is None:
        return 1.0
    return float(multiplier)


def upgrade_user_plan(
    db: Session,
    user_id: UUID,
    plan_name: str,
    duration_days: int = 30,
) -> UserSubscription:
    """Upgrade user to a new plan."""
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == plan_name).first()

    if not plan:
        raise ValueError(f"Plan '{plan_name}' not found")

    # Cancel existing subscription
    existing = get_user_subscription(db, user_id)
    if existing:
        existing.status = "cancelled"
        existing.cancelled_at = datetime.utcnow()

    # Create new subscription
    now = datetime.utcnow()
    subscription = UserSubscription(
        user_id=user_id,
        plan_id=plan.id,
        status="active",
        started_at=now,
        expires_at=now + timedelta(days=duration_days) if duration_days > 0 else None,
        current_period_start=now,
        current_period_end=now + timedelta(days=duration_days) if duration_days > 0 else None,
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


def check_quota(
    db: Session,
    user_id: UUID,
    quota_type: str,
) -> tuple[bool, int, int | None]:
    """
    Check if user is within quota limits.

    Args:
        db: Database session
        user_id: User ID
        quota_type: Type of quota ('jobs', 'storage', 'api_calls')

    Returns:
        Tuple of (is_within_quota, current_usage, limit)
        limit is None for unlimited
    """
    plan = get_user_plan(db, user_id)
    usage = get_current_period_usage(db, user_id)

    # Map quota types to plan limits
    limits = {
        "jobs": plan.max_jobs_per_month,
        "storage": plan.max_storage_mb,
        "api_calls": plan.max_api_calls_per_day,
    }

    # Map quota types to usage counters
    current = {
        "jobs": usage.jobs_created if usage else 0,
        "storage": usage.storage_used_mb if usage else 0,
        "api_calls": usage.api_calls if usage else 0,
    }

    limit = limits.get(quota_type)
    current_value = current.get(quota_type, 0)

    if limit is None:
        # Unlimited
        return True, current_value, None

    return current_value < limit, current_value, limit


def increment_usage(
    db: Session,
    user_id: UUID,
    metric: str,
    amount: int = 1,
) -> None:
    """
    Increment usage metric for current period.

    Args:
        db: Database session
        user_id: User ID
        metric: Metric to increment ('api_calls', 'jobs', 'storage', 'compute')
        amount: Amount to increment by
    """
    now = datetime.utcnow()
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Calculate period end (first day of next month)
    if period_start.month == 12:
        period_end = period_start.replace(year=period_start.year + 1, month=1)
    else:
        period_end = period_start.replace(month=period_start.month + 1)

    usage = (
        db.query(UserUsage)
        .filter(
            UserUsage.user_id == user_id,
            UserUsage.period_start == period_start,
        )
        .first()
    )

    if not usage:
        usage = UserUsage(
            user_id=user_id,
            period_start=period_start,
            period_end=period_end,
        )
        db.add(usage)

    # Increment the specific metric
    if metric == "api_calls":
        usage.api_calls += amount
    elif metric == "jobs":
        usage.jobs_created += amount
    elif metric == "storage":
        usage.storage_used_mb += amount
    elif metric == "compute":
        usage.compute_minutes += amount
    else:
        raise ValueError(f"Unknown metric: {metric}")

    db.commit()


def get_current_period_usage(db: Session, user_id: UUID) -> UserUsage | None:
    """Get usage for current billing period."""
    now = datetime.utcnow()
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    return (
        db.query(UserUsage)
        .filter(
            UserUsage.user_id == user_id,
            UserUsage.period_start == period_start,
        )
        .first()
    )


__all__ = [
    "get_user_subscription",
    "get_user_plan",
    "has_feature",
    "get_rate_limit_multiplier",
    "upgrade_user_plan",
    "check_quota",
    "increment_usage",
    "get_current_period_usage",
]
