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
    LockActionResponse,
    ResetTwoFAResponse,
    ResendVerificationResponse,
    RoleUpdateRequest,
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
