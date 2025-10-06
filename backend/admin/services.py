"""Business logic for admin user and audit operations."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Iterable
from uuid import UUID

import structlog
from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from backend.admin.audit import hash_email, record_admin_event
from backend.admin.schemas import (
    AdminUser,
    AdminUserListResponse,
    AuditLogEntry,
    AuditLogListResponse,
    LockActionResponse,
    ResetTwoFAResponse,
    ResendVerificationResponse,
)
from backend.auth.schemas import ResendVerificationRequest
from backend.auth.service.registration_service import resend_verification as resend_verification_flow
from backend.db.models.audit import AuditLog
from backend.db.models.user import Role, User, UserStatus

logger = structlog.get_logger(__name__)

ALLOWED_ROLE_NAMES = {"ADMIN", "USER", "BILLING_ADMIN", "SUPPORT"}
DEFAULT_SORT = "created_at_desc"
AUDIT_EXPORT_HEADERS = [
    "id",
    "actor_user_id",
    "action",
    "target_type",
    "target_id",
    "ip",
    "user_agent",
    "metadata",
    "created_at",
]


class AdminUserService:
    """Encapsulates admin-focused user management operations."""

    def __init__(self, session: Session):
        self._session = session

    def _base_query(self) -> Select[tuple[User]]:
        return select(User).options(selectinload(User.roles))

    def _apply_filters(
        self,
        stmt: Select[Any],
        *,
        q: str | None,
        status_filter: str | None,
        role_filter: str | None,
    ) -> Select[Any]:
        if q:
            stmt = stmt.where(func.lower(User.email).contains(q.lower()))
        if status_filter:
            try:
                status_enum = UserStatus(status_filter)
            except ValueError as exc:  # pragma: no cover - validated upstream
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status filter.") from exc
            stmt = stmt.where(User.status == status_enum)
        if role_filter:
            normalized_role = role_filter.upper()
            if normalized_role not in ALLOWED_ROLE_NAMES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid role filter.",
                )
            stmt = stmt.join(Role, User.roles).where(Role.name == normalized_role)
        return stmt

    def list_users(
        self,
        *,
        q: str | None,
        status_filter: str | None,
        role_filter: str | None,
        page: int,
        page_size: int,
        sort: str,
    ) -> AdminUserListResponse:
        stmt = self._base_query()
        stmt = self._apply_filters(stmt, q=q, status_filter=status_filter, role_filter=role_filter)
        if role_filter:
            stmt = stmt.distinct()

        ids_stmt = select(User.id)
        ids_stmt = self._apply_filters(ids_stmt, q=q, status_filter=status_filter, role_filter=role_filter)
        if role_filter:
            ids_stmt = ids_stmt.distinct()
        total = self._session.scalar(select(func.count()).select_from(ids_stmt.subquery())) or 0

        order_by = User.created_at.desc()
        if sort == "created_at_asc":
            order_by = User.created_at.asc()
        elif sort and sort != DEFAULT_SORT:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid sort value.")

        stmt = stmt.order_by(order_by).offset((page - 1) * page_size).limit(page_size)
        users = self._session.execute(stmt).scalars().unique().all()
        items = [self._to_schema(user) for user in users]
        logger.info(
            "admin.users.listed",
            query=q,
            status=status_filter,
            role=role_filter,
            page=page,
            page_size=page_size,
            total=total,
        )
        return AdminUserListResponse(items=items, page=page, page_size=page_size, total=total)

    def _to_schema(self, user: User) -> AdminUser:
        return AdminUser(
            id=user.id,
            email=user.email,
            status=user.status,
            roles=[role.name for role in user.roles],
            created_at=user.created_at,
            mfa_enabled=user.mfa_enabled,
            email_verified=user.email_verified_at is not None,
        )

    def get_user(self, user_id: UUID) -> User:
        stmt = self._base_query().where(User.id == user_id)
        user = self._session.execute(stmt).scalars().first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        return user

    def update_roles(
        self,
        *,
        actor: User,
        target: User,
        roles: Iterable[str],
        ip: str | None,
        user_agent: str | None,
    ) -> AdminUser:
        requested = {role.upper() for role in roles}
        if not requested.issubset(ALLOWED_ROLE_NAMES):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role selection.")

        role_stmt = select(Role).where(Role.name.in_(requested))
        existing_roles = self._session.execute(role_stmt).scalars().all()
        found = {role.name for role in existing_roles}
        missing = requested - found
        if missing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown roles: {', '.join(sorted(missing))}.")

        target.roles = list(existing_roles)
        self._session.flush()

        record_admin_event(
            self._session,
            actor_user_id=actor.id,
            target_user_id=target.id,
            action="user_roles_changed",
            metadata={"roles": sorted(requested), "email_hash": hash_email(target.email)},
            ip=ip,
            user_agent=user_agent,
        )
        logger.info(
            "admin.users.roles_updated",
            actor_user_id=str(actor.id),
            target_user_id=str(target.id),
            roles=sorted(requested),
        )
        return self._to_schema(target)

    def lock_user(
        self,
        *,
        actor: User,
        target: User,
        ip: str | None,
        user_agent: str | None,
    ) -> LockActionResponse:
        previous_status = target.status
        target.status = UserStatus.DISABLED
        self._session.flush()

        record_admin_event(
            self._session,
            actor_user_id=actor.id,
            target_user_id=target.id,
            action="user_locked",
            metadata={
                "previous_status": previous_status.value,
                "email_hash": hash_email(target.email),
            },
            ip=ip,
            user_agent=user_agent,
        )
        logger.info(
            "admin.users.locked",
            actor_user_id=str(actor.id),
            target_user_id=str(target.id),
        )
        return LockActionResponse(user=self._to_schema(target))

    def unlock_user(
        self,
        *,
        actor: User,
        target: User,
        ip: str | None,
        user_agent: str | None,
    ) -> LockActionResponse:
        if target.email_verified_at is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User must verify email before unlocking.",
            )

        target.status = UserStatus.ACTIVE
        self._session.flush()

        record_admin_event(
            self._session,
            actor_user_id=actor.id,
            target_user_id=target.id,
            action="user_unlocked",
            metadata={"email_hash": hash_email(target.email)},
            ip=ip,
            user_agent=user_agent,
        )
        logger.info(
            "admin.users.unlocked",
            actor_user_id=str(actor.id),
            target_user_id=str(target.id),
        )
        return LockActionResponse(user=self._to_schema(target))

    def reset_two_factor(
        self,
        *,
        actor: User,
        target: User,
        ip: str | None,
        user_agent: str | None,
    ) -> ResetTwoFAResponse:
        target.mfa_secret = None
        target.recovery_codes = None
        target.mfa_enabled = False
        self._session.flush()

        record_admin_event(
            self._session,
            actor_user_id=actor.id,
            target_user_id=target.id,
            action="admin_reset_2fa",
            metadata={"email_hash": hash_email(target.email)},
            ip=ip,
            user_agent=user_agent,
        )
        logger.info(
            "admin.users.reset_2fa",
            actor_user_id=str(actor.id),
            target_user_id=str(target.id),
        )
        return ResetTwoFAResponse(user=self._to_schema(target))

    async def resend_verification(
        self,
        *,
        actor: User,
        target: User,
        settings,
        redis: Redis,
        ip: str | None,
        user_agent: str | None,
    ) -> ResendVerificationResponse:
        if target.status != UserStatus.UNVERIFIED:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is already verified.")

        request = ResendVerificationRequest(email=target.email)
        message = await resend_verification_flow(session=self._session, request=request, settings=settings, redis=redis)

        record_admin_event(
            self._session,
            actor_user_id=actor.id,
            target_user_id=target.id,
            action="admin_resend_verification",
            metadata={"email_hash": hash_email(target.email)},
            ip=ip,
            user_agent=user_agent,
        )
        logger.info(
            "admin.users.resend_verification",
            actor_user_id=str(actor.id),
            target_user_id=str(target.id),
        )
        return ResendVerificationResponse(message=message)


class AuditLogService:
    """Audit log querying and export helpers."""

    def __init__(self, session: Session):
        self._session = session

    def _base_query(self) -> Select[tuple[AuditLog]]:
        return select(AuditLog).order_by(AuditLog.created_at.desc())

    def _apply_filters(
        self,
        stmt: Select[Any],
        *,
        actor: str | None,
        action: str | None,
        target_type: str | None,
        from_ts: datetime | None,
        to_ts: datetime | None,
    ) -> Select[Any]:
        if actor:
            stmt = stmt.where(AuditLog.actor_user_id == actor)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if target_type:
            stmt = stmt.where(AuditLog.target_type == target_type)
        if from_ts:
            stmt = stmt.where(AuditLog.created_at >= from_ts)
        if to_ts:
            stmt = stmt.where(AuditLog.created_at <= to_ts)
        return stmt

    def list_logs(
        self,
        *,
        actor: str | None,
        action: str | None,
        target_type: str | None,
        from_ts: datetime | None,
        to_ts: datetime | None,
        page: int,
        page_size: int,
    ) -> AuditLogListResponse:
        stmt = self._base_query()
        stmt = self._apply_filters(stmt, actor=actor, action=action, target_type=target_type, from_ts=from_ts, to_ts=to_ts)

        total_stmt = select(func.count(AuditLog.id))
        total_stmt = self._apply_filters(total_stmt, actor=actor, action=action, target_type=target_type, from_ts=from_ts, to_ts=to_ts)
        total = self._session.scalar(total_stmt) or 0

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        records = self._session.execute(stmt).scalars().all()
        items = [self._to_schema(record) for record in records]
        logger.info(
            "admin.audit.listed",
            actor=actor,
            action=action,
            target_type=target_type,
            page=page,
            page_size=page_size,
            total=total,
        )
        return AuditLogListResponse(items=items, page=page, page_size=page_size, total=total)

    def stream_csv(
        self,
        *,
        actor: str | None,
        action: str | None,
        target_type: str | None,
        from_ts: datetime | None,
        to_ts: datetime | None,
        batch_size: int = 500,
    ):
        stmt = self._base_query()
        stmt = self._apply_filters(stmt, actor=actor, action=action, target_type=target_type, from_ts=from_ts, to_ts=to_ts)

        yield ",".join(AUDIT_EXPORT_HEADERS) + "\n"

        offset = 0
        while True:
            batch_stmt = stmt.offset(offset).limit(batch_size)
            records = self._session.execute(batch_stmt).scalars().all()
            if not records:
                break
            for record in records:
                metadata = json.dumps(record.metadata_json or {}, separators=(",", ":"))
                row = [
                    str(record.id),
                    str(record.actor_user_id) if record.actor_user_id else "",
                    record.action,
                    record.target_type or "",
                    record.target_id or "",
                    record.ip or "",
                    record.user_agent or "",
                    metadata,
                    record.created_at.isoformat() if record.created_at else "",
                ]
                yield ",".join(_escape_csv_field(value) for value in row) + "\n"
            offset += batch_size
        logger.info("admin.audit.export_stream_completed", actor=actor, action=action, target_type=target_type)

    def _to_schema(self, record: AuditLog) -> AuditLogEntry:
        return AuditLogEntry(
            id=record.id,
            actor_user_id=record.actor_user_id,
            action=record.action,
            target_type=record.target_type,
            target_id=record.target_id,
            metadata_json=record.metadata_json,
            ip=record.ip,
            user_agent=record.user_agent,
            created_at=record.created_at,
        )


def _escape_csv_field(value: str) -> str:
    if "," in value or "\n" in value or "\"" in value:
        escaped = value.replace("\"", "\"\"")
        return f'"{escaped}"'
    return value


__all__ = ["AdminUserService", "AuditLogService", "ALLOWED_ROLE_NAMES"]
