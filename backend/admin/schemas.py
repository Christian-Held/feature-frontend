"""Pydantic schemas for admin APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.generics import GenericModel

from backend.db.models.user import UserStatus

T = TypeVar("T")


class PaginatedResponse(GenericModel, Generic[T]):
    """Generic pagination envelope."""

    items: list[T]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total: int = Field(ge=0)


class AdminUser(BaseModel):
    """Summary information about a managed user."""

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: UUID
    email: str
    status: UserStatus
    roles: list[str]
    created_at: datetime
    mfa_enabled: bool
    email_verified: bool


class AdminUserListResponse(PaginatedResponse[AdminUser]):
    """Paginated users response."""


class RoleUpdateRequest(BaseModel):
    """Payload for updating a user's roles."""

    roles: list[str]


class LockActionResponse(BaseModel):
    """Response body after mutating a user's status."""

    user: AdminUser


class ResetTwoFAResponse(BaseModel):
    """Response body for MFA reset operations."""

    user: AdminUser


class ResendVerificationResponse(BaseModel):
    """Response returned when a verification email is re-enqueued."""

    message: str


class AuditLogEntry(BaseModel):
    """Audit log entry returned to clients."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    actor_user_id: UUID | None
    action: str
    target_type: str | None
    target_id: str | None
    metadata: dict[str, Any] | None = Field(default=None, alias="metadata_json")
    ip: str | None
    user_agent: str | None
    created_at: datetime


class AuditLogListResponse(PaginatedResponse[AuditLogEntry]):
    """Paginated audit log listing."""


class PlatformStats(BaseModel):
    """Platform-wide statistics for admin dashboard."""

    total_users: int
    active_users: int
    unverified_users: int
    disabled_users: int
    superadmins: int

    users_with_mfa: int

    total_sessions: int
    active_sessions: int

    subscriptions_by_plan: dict[str, int]
    total_active_subscriptions: int

    # Usage stats (current month)
    total_api_calls: int
    total_jobs_created: int
    total_storage_mb: int


class RevokeSessionsResponse(BaseModel):
    """Response after revoking user sessions."""

    revoked_count: int
    user_id: UUID


class ClearRateLimitResponse(BaseModel):
    """Response after clearing rate limits."""

    success: bool
    message: str


class UpgradeUserPlanRequest(BaseModel):
    """Request to upgrade a user's subscription plan."""

    plan_name: str
    duration_days: int | None = None


class UpgradeUserPlanResponse(BaseModel):
    """Response after upgrading user's plan."""

    user_id: UUID
    plan_name: str
    subscription_id: UUID
    expires_at: datetime | None


__all__ = [
    "AdminUser",
    "AdminUserListResponse",
    "AuditLogEntry",
    "AuditLogListResponse",
    "PaginatedResponse",
    "ResendVerificationResponse",
    "ResetTwoFAResponse",
    "RoleUpdateRequest",
    "LockActionResponse",
    "PlatformStats",
    "RevokeSessionsResponse",
    "ClearRateLimitResponse",
    "UpgradeUserPlanRequest",
    "UpgradeUserPlanResponse",
]
