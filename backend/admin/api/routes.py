"""FastAPI routes for admin RBAC, user management, and audit logs."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from backend.admin.dependencies import require_admin_user
from backend.admin.rate_limits import (
    ADMIN_AUDIT_LOGS_PER_MINUTE,
    ADMIN_LIST_WINDOW_SECONDS,
    ADMIN_MUTATION_PER_MINUTE,
    ADMIN_MUTATION_WINDOW_SECONDS,
    ADMIN_USERS_PER_MINUTE,
)
from backend.admin.schemas import (
    AdminUser,
    AdminUserListResponse,
    AuditLogListResponse,
    ClearRateLimitResponse,
    LockActionResponse,
    PlatformStats,
    ResetTwoFAResponse,
    ResendVerificationResponse,
    RevokeSessionsResponse,
    RoleUpdateRequest,
    UpgradeUserPlanRequest,
    UpgradeUserPlanResponse,
)
from backend.admin.services import AdminUserService, AuditLogService, ALLOWED_ROLE_NAMES
from backend.auth.service.rate_limit import enforce_rate_limit
from backend.core.config import AppConfig, get_settings
from backend.db.models.user import User, UserStatus
from backend.db.session import get_db
from backend.redis.client import get_redis_client

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1/admin", tags=["admin"])


def _client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return None


def _user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    request: Request,
    q: str | None = Query(default=None, description="Filter by email substring."),
    status_filter: UserStatus | None = Query(default=None, alias="status"),
    role: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort: str = Query(default="created_at_desc"),
    session: Session = Depends(get_db),
    admin_user: User = Depends(require_admin_user),
    settings: AppConfig = Depends(get_settings),
    redis: Redis = Depends(get_redis_client),
) -> AdminUserListResponse:
    await enforce_rate_limit(
        redis,
        settings=settings,
        scope="admin:users:list",
        identifier=str(admin_user.id),
        limit=ADMIN_USERS_PER_MINUTE,
        window_seconds=ADMIN_LIST_WINDOW_SECONDS,
    )

    if role and role.upper() not in ALLOWED_ROLE_NAMES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role filter.")

    service = AdminUserService(session)
    response = service.list_users(
        q=q,
        status_filter=status_filter.value if status_filter else None,
        role_filter=role.upper() if role else None,
        page=page,
        page_size=page_size,
        sort=sort,
    )
    return response


@router.post("/users/{user_id}/roles", response_model=AdminUser)
async def update_roles(
    request: Request,
    user_id: UUID,
    payload: RoleUpdateRequest,
    session: Session = Depends(get_db),
    admin_user: User = Depends(require_admin_user),
    settings: AppConfig = Depends(get_settings),
    redis: Redis = Depends(get_redis_client),
):
    await _enforce_mutation_limit(redis, settings=settings, admin_user=admin_user, target_user_id=user_id)

    if payload.roles and any(role.upper() not in ALLOWED_ROLE_NAMES for role in payload.roles):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role selection.")

    service = AdminUserService(session)
    target = service.get_user(user_id)
    updated = service.update_roles(
        actor=admin_user,
        target=target,
        roles=payload.roles,
        ip=_client_ip(request),
        user_agent=_user_agent(request),
    )
    session.commit()
    return updated


@router.post("/users/{user_id}/lock", response_model=LockActionResponse)
async def lock_user(
    request: Request,
    user_id: UUID,
    session: Session = Depends(get_db),
    admin_user: User = Depends(require_admin_user),
    settings: AppConfig = Depends(get_settings),
    redis: Redis = Depends(get_redis_client),
) -> LockActionResponse:
    await _enforce_mutation_limit(redis, settings=settings, admin_user=admin_user, target_user_id=user_id)

    service = AdminUserService(session)
    target = service.get_user(user_id)
    response = service.lock_user(
        actor=admin_user,
        target=target,
        ip=_client_ip(request),
        user_agent=_user_agent(request),
    )
    session.commit()
    return response


@router.post("/users/{user_id}/unlock", response_model=LockActionResponse)
async def unlock_user(
    request: Request,
    user_id: UUID,
    session: Session = Depends(get_db),
    admin_user: User = Depends(require_admin_user),
    settings: AppConfig = Depends(get_settings),
    redis: Redis = Depends(get_redis_client),
) -> LockActionResponse:
    await _enforce_mutation_limit(redis, settings=settings, admin_user=admin_user, target_user_id=user_id)

    service = AdminUserService(session)
    target = service.get_user(user_id)
    response = service.unlock_user(
        actor=admin_user,
        target=target,
        ip=_client_ip(request),
        user_agent=_user_agent(request),
    )
    session.commit()
    return response


@router.post("/users/{user_id}/reset-2fa", response_model=ResetTwoFAResponse)
async def reset_two_factor(
    request: Request,
    user_id: UUID,
    session: Session = Depends(get_db),
    admin_user: User = Depends(require_admin_user),
    settings: AppConfig = Depends(get_settings),
    redis: Redis = Depends(get_redis_client),
) -> ResetTwoFAResponse:
    await _enforce_mutation_limit(redis, settings=settings, admin_user=admin_user, target_user_id=user_id)

    service = AdminUserService(session)
    target = service.get_user(user_id)
    response = service.reset_two_factor(
        actor=admin_user,
        target=target,
        ip=_client_ip(request),
        user_agent=_user_agent(request),
    )
    session.commit()
    return response


@router.post("/users/{user_id}/resend-verification", response_model=ResendVerificationResponse)
async def resend_verification(
    request: Request,
    user_id: UUID,
    session: Session = Depends(get_db),
    admin_user: User = Depends(require_admin_user),
    settings: AppConfig = Depends(get_settings),
    redis: Redis = Depends(get_redis_client),
) -> ResendVerificationResponse:
    await _enforce_mutation_limit(redis, settings=settings, admin_user=admin_user, target_user_id=user_id)

    service = AdminUserService(session)
    target = service.get_user(user_id)
    response = await service.resend_verification(
        actor=admin_user,
        target=target,
        settings=settings,
        redis=redis,
        ip=_client_ip(request),
        user_agent=_user_agent(request),
    )
    session.commit()
    return response


@router.get("/audit-logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    actor: str | None = Query(default=None),
    action: str | None = Query(default=None),
    target_type: str | None = Query(default=None),
    from_ts: datetime | None = Query(default=None, alias="from"),
    to_ts: datetime | None = Query(default=None, alias="to"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_db),
    admin_user: User = Depends(require_admin_user),
    settings: AppConfig = Depends(get_settings),
    redis: Redis = Depends(get_redis_client),
) -> AuditLogListResponse:
    await enforce_rate_limit(
        redis,
        settings=settings,
        scope="admin:audit:list",
        identifier=str(admin_user.id),
        limit=ADMIN_AUDIT_LOGS_PER_MINUTE,
        window_seconds=ADMIN_LIST_WINDOW_SECONDS,
    )

    service = AuditLogService(session)
    return service.list_logs(
        actor=actor,
        action=action,
        target_type=target_type,
        from_ts=from_ts,
        to_ts=to_ts,
        page=page,
        page_size=page_size,
    )


@router.get("/audit-logs/export")
async def export_audit_logs(
    format: str = Query(alias="format", pattern="^csv$"),
    actor: str | None = Query(default=None),
    action: str | None = Query(default=None),
    target_type: str | None = Query(default=None),
    from_ts: datetime | None = Query(default=None, alias="from"),
    to_ts: datetime | None = Query(default=None, alias="to"),
    session: Session = Depends(get_db),
    admin_user: User = Depends(require_admin_user),
    settings: AppConfig = Depends(get_settings),
    redis: Redis = Depends(get_redis_client),
):
    if format.lower() != "csv":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported export format.")

    await enforce_rate_limit(
        redis,
        settings=settings,
        scope="admin:audit:list",
        identifier=str(admin_user.id),
        limit=ADMIN_AUDIT_LOGS_PER_MINUTE,
        window_seconds=ADMIN_LIST_WINDOW_SECONDS,
    )

    service = AuditLogService(session)
    stream = service.stream_csv(
        actor=actor,
        action=action,
        target_type=target_type,
        from_ts=from_ts,
        to_ts=to_ts,
    )
    headers = {"Content-Disposition": "attachment; filename=admin-audit-logs.csv"}
    return StreamingResponse(stream, media_type="text/csv", headers=headers)


@router.get("/stats", response_model=PlatformStats)
async def get_platform_stats(
    session: Session = Depends(get_db),
    admin_user: User = Depends(require_admin_user),
    settings: AppConfig = Depends(get_settings),
    redis: Redis = Depends(get_redis_client),
) -> PlatformStats:
    """Get platform-wide statistics."""
    await enforce_rate_limit(
        redis,
        settings=settings,
        scope="admin:stats",
        identifier=str(admin_user.id),
        limit=ADMIN_USERS_PER_MINUTE,
        window_seconds=ADMIN_LIST_WINDOW_SECONDS,
    )

    from backend.db.models.subscription_plan import SubscriptionPlan
    from backend.db.models.user_subscription import UserSubscription
    from backend.db.models.user_usage import UserUsage
    from backend.db.models.user import Session as UserSession
    from sqlalchemy import func
    from datetime import datetime

    # User counts
    total_users = session.query(func.count(User.id)).scalar() or 0
    active_users = session.query(func.count(User.id)).filter(User.status == UserStatus.ACTIVE).scalar() or 0
    unverified_users = session.query(func.count(User.id)).filter(User.status == UserStatus.UNVERIFIED).scalar() or 0
    disabled_users = session.query(func.count(User.id)).filter(User.status == UserStatus.DISABLED).scalar() or 0
    superadmins = session.query(func.count(User.id)).filter(User.is_superadmin == True).scalar() or 0
    users_with_mfa = session.query(func.count(User.id)).filter(User.mfa_enabled == True).scalar() or 0

    # Session counts
    total_sessions = session.query(func.count(UserSession.id)).scalar() or 0
    active_sessions = (
        session.query(func.count(UserSession.id))
        .filter(
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > datetime.utcnow()
        )
        .scalar() or 0
    )

    # Subscription counts by plan
    subscriptions_by_plan_query = (
        session.query(SubscriptionPlan.name, func.count(UserSubscription.id))
        .outerjoin(UserSubscription, SubscriptionPlan.id == UserSubscription.plan_id)
        .filter(UserSubscription.status == "active")
        .group_by(SubscriptionPlan.name)
        .all()
    )
    subscriptions_by_plan = {name: count for name, count in subscriptions_by_plan_query}
    total_active_subscriptions = sum(subscriptions_by_plan.values())

    # Usage stats (current month)
    now = datetime.utcnow()
    current_month_start = datetime(now.year, now.month, 1)

    usage_stats = (
        session.query(
            func.sum(UserUsage.api_calls),
            func.sum(UserUsage.jobs_created),
            func.sum(UserUsage.storage_used_mb)
        )
        .filter(UserUsage.period_start >= current_month_start)
        .first()
    )

    total_api_calls = usage_stats[0] or 0
    total_jobs_created = usage_stats[1] or 0
    total_storage_mb = usage_stats[2] or 0

    return PlatformStats(
        total_users=total_users,
        active_users=active_users,
        unverified_users=unverified_users,
        disabled_users=disabled_users,
        superadmins=superadmins,
        users_with_mfa=users_with_mfa,
        total_sessions=total_sessions,
        active_sessions=active_sessions,
        subscriptions_by_plan=subscriptions_by_plan,
        total_active_subscriptions=total_active_subscriptions,
        total_api_calls=total_api_calls,
        total_jobs_created=total_jobs_created,
        total_storage_mb=total_storage_mb,
    )


@router.post("/users/{user_id}/revoke-sessions", response_model=RevokeSessionsResponse)
async def revoke_user_sessions(
    request: Request,
    user_id: UUID,
    session: Session = Depends(get_db),
    admin_user: User = Depends(require_admin_user),
    settings: AppConfig = Depends(get_settings),
    redis: Redis = Depends(get_redis_client),
) -> RevokeSessionsResponse:
    """Revoke all sessions for a specific user."""
    await _enforce_mutation_limit(redis, settings=settings, admin_user=admin_user, target_user_id=user_id)

    from backend.db.models.user import Session as UserSession
    from datetime import datetime

    # Update all active sessions for this user
    revoked_count = (
        session.query(UserSession)
        .filter(
            UserSession.user_id == user_id,
            UserSession.revoked_at.is_(None)
        )
        .update({"revoked_at": datetime.utcnow()}, synchronize_session=False)
    )

    session.commit()

    logger.info(
        "admin_revoked_user_sessions",
        admin_id=str(admin_user.id),
        target_user_id=str(user_id),
        revoked_count=revoked_count,
        ip=_client_ip(request),
    )

    return RevokeSessionsResponse(revoked_count=revoked_count, user_id=user_id)


@router.post("/users/{user_id}/clear-rate-limits", response_model=ClearRateLimitResponse)
async def clear_user_rate_limits(
    request: Request,
    user_id: UUID,
    session: Session = Depends(get_db),
    admin_user: User = Depends(require_admin_user),
    settings: AppConfig = Depends(get_settings),
    redis: Redis = Depends(get_redis_client),
) -> ClearRateLimitResponse:
    """Clear all rate limits for a specific user."""
    await _enforce_mutation_limit(redis, settings=settings, admin_user=admin_user, target_user_id=user_id)

    # Get all rate limit keys for this user from Redis
    # Pattern: {prefix}:*:{user_id}
    prefix = settings.redis_rate_limit_prefix
    pattern = f"{prefix}:*:{user_id}*"

    keys_deleted = 0
    cursor = 0
    while True:
        cursor, keys = await redis.scan(cursor, match=pattern, count=100)
        if keys:
            keys_deleted += await redis.delete(*keys)
        if cursor == 0:
            break

    logger.info(
        "admin_cleared_rate_limits",
        admin_id=str(admin_user.id),
        target_user_id=str(user_id),
        keys_deleted=keys_deleted,
        ip=_client_ip(request),
    )

    return ClearRateLimitResponse(
        success=True,
        message=f"Cleared {keys_deleted} rate limit keys for user {user_id}"
    )


@router.post("/users/{user_id}/upgrade-plan", response_model=UpgradeUserPlanResponse)
async def upgrade_user_plan(
    request: Request,
    user_id: UUID,
    payload: UpgradeUserPlanRequest,
    session: Session = Depends(get_db),
    admin_user: User = Depends(require_admin_user),
    settings: AppConfig = Depends(get_settings),
    redis: Redis = Depends(get_redis_client),
) -> UpgradeUserPlanResponse:
    """Upgrade or change a user's subscription plan (admin action)."""
    await _enforce_mutation_limit(redis, settings=settings, admin_user=admin_user, target_user_id=user_id)

    from backend.subscription import service as subscription_service

    # Verify user exists
    target_user = session.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Upgrade the plan
    try:
        subscription = subscription_service.upgrade_user_plan(
            session,
            user_id,
            payload.plan_name,
            duration_days=payload.duration_days
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    session.commit()

    logger.info(
        "admin_upgraded_user_plan",
        admin_id=str(admin_user.id),
        target_user_id=str(user_id),
        plan_name=payload.plan_name,
        duration_days=payload.duration_days,
        ip=_client_ip(request),
    )

    return UpgradeUserPlanResponse(
        user_id=user_id,
        plan_name=payload.plan_name,
        subscription_id=subscription.id,
        expires_at=subscription.expires_at,
    )


async def _enforce_mutation_limit(
    redis: Redis,
    *,
    settings: AppConfig,
    admin_user: User,
    target_user_id: UUID,
) -> None:
    await enforce_rate_limit(
        redis,
        settings=settings,
        scope="admin:user:mutate",
        identifier=f"{admin_user.id}:{target_user_id}",
        limit=ADMIN_MUTATION_PER_MINUTE,
        window_seconds=ADMIN_MUTATION_WINDOW_SECONDS,
    )


__all__ = ["router"]
