"""User-related ORM models."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, JSON, LargeBinary, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from backend.db.types import GUID


class UserStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    UNVERIFIED = "UNVERIFIED"
    DISABLED = "DISABLED"


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Represents a platform user."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus, name="user_status"), default=UserStatus.UNVERIFIED, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    mfa_secret: Mapped[bytes | None] = mapped_column(LargeBinary)
    recovery_codes: Mapped[dict | None] = mapped_column(JSON, default=None)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_ip: Mapped[str | None] = mapped_column(String(45))

    roles: Mapped[list["Role"]] = relationship("Role", secondary="user_roles", back_populates="users")
    sessions: Mapped[list["Session"]] = relationship("Session", back_populates="user")
    plans: Mapped[list["UserPlan"]] = relationship("UserPlan", back_populates="user")


class EmailVerification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Email verification tokens tied to a user."""

    __tablename__ = "email_verifications"

    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PasswordReset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Password reset tokens for recovery flows."""

    __tablename__ = "password_resets"

    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Role(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Role definitions for RBAC."""

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))

    users: Mapped[list["User"]] = relationship("User", secondary="user_roles", back_populates="roles")


class UserRole(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Mapping between users and roles."""

    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),)

    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)


class Session(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Refresh token sessions for the authentication service."""

    __tablename__ = "sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    refresh_token_hash: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_agent: Mapped[str | None] = mapped_column(String(512))
    ip: Mapped[str | None] = mapped_column(String(45))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship("User", back_populates="sessions")


__all__ = [
    "User",
    "EmailVerification",
    "PasswordReset",
    "Role",
    "UserRole",
    "Session",
    "UserStatus",
]

