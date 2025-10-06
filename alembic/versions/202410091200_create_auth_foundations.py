"""create auth foundations"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from backend.core.config import get_settings
from backend.security.passwords import PasswordHashingService


revision = "202410091200"
down_revision = None
branch_labels = None
depends_on = None


user_status_enum = postgresql.ENUM("ACTIVE", "UNVERIFIED", "DISABLED", name="user_status")
plan_status_enum = postgresql.ENUM("ACTIVE", "CANCELED", "PAST_DUE", name="plan_status")


def upgrade() -> None:
    user_status_enum.create(op.get_bind(), checkfirst=True)
    plan_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("email_verified_at", sa.DateTime(timezone=True)),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "UNVERIFIED", "DISABLED", name="user_status", create_type=False),
            nullable=False,
            server_default="UNVERIFIED",
        ),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("mfa_secret", sa.LargeBinary()),
        sa.Column("recovery_codes", sa.JSON()),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("last_ip", sa.String(length=45)),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False, unique=True),
        sa.Column("description", sa.String(length=255)),
    )

    op.create_table(
        "plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False, unique=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("monthly_price_usd", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("metadata", sa.JSON()),
    )

    op.create_table(
        "email_verifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=256), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_email_verifications_token_hash", "email_verifications", ["token_hash"], unique=False)

    op.create_table(
        "password_resets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=256), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_password_resets_token_hash", "password_resets", ["token_hash"], unique=False)

    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=256), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rotated_at", sa.DateTime(timezone=True)),
        sa.Column("user_agent", sa.String(length=512)),
        sa.Column("ip", sa.String(length=45)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"], unique=False)
    op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("target_type", sa.String(length=64)),
        sa.Column("target_id", sa.String(length=128)),
        sa.Column("ip", sa.String(length=45)),
        sa.Column("user_agent", sa.String(length=512)),
        sa.Column("metadata", sa.JSON()),
        sa.Column("occurred_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "spend_limits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("monthly_cap_usd", sa.Numeric(10, 2), nullable=False),
        sa.Column("hard_stop", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.UniqueConstraint("user_id", name="uq_spend_limits_user"),
    )

    op.create_table(
        "user_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),
    )

    op.create_table(
        "user_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "CANCELED", "PAST_DUE", name="plan_status", create_type=False),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column("renews_at", sa.DateTime(timezone=True)),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("user_id", "plan_id", name="uq_user_plans_user_plan"),
    )

    seed_admin()


def downgrade() -> None:
    op.drop_table("user_plans")
    op.drop_table("user_roles")
    op.drop_table("spend_limits")
    op.drop_table("audit_logs")
    op.drop_table("sessions")
    op.drop_table("password_resets")
    op.drop_table("email_verifications")
    op.drop_table("plans")
    op.drop_table("roles")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    plan_status_enum.drop(op.get_bind(), checkfirst=True)
    user_status_enum.drop(op.get_bind(), checkfirst=True)


def seed_admin() -> None:
    settings = get_settings()
    hasher = PasswordHashingService(settings)
    conn = op.get_bind()

    roles_table = sa.table(
        "roles",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String()),
        sa.column("description", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )

    now = datetime.now(timezone.utc)
    role_names = {
        "ADMIN": "Full administrative access",
        "USER": "Standard end-user",
        "BILLING_ADMIN": "Billing and subscription management",
        "SUPPORT": "Support tooling access",
    }

    existing_roles = {
        row[0]
        for row in conn.execute(sa.select(roles_table.c.name))  # type: ignore[attr-defined]
    }

    for name, description in role_names.items():
        if name not in existing_roles:
            conn.execute(
                roles_table.insert().values(  # type: ignore[attr-defined]
                    id=uuid.uuid4(),
                    name=name,
                    description=description,
                    created_at=now,
                    updated_at=now,
                )
            )

    users_table = sa.table(
        "users",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("email", sa.String()),
        sa.column("password_hash", sa.String()),
        sa.column("status", sa.Enum("ACTIVE", "UNVERIFIED", "DISABLED", name="user_status", create_type=False)),
        sa.column("email_verified_at", sa.DateTime(timezone=True)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
        sa.column("mfa_enabled", sa.Boolean()),
    )

    admin_email = settings.admin_email.lower()
    admin_exists = conn.execute(
        sa.select(users_table.c.id).where(sa.func.lower(users_table.c.email) == admin_email)  # type: ignore[attr-defined]
    ).first()

    if admin_exists:
        return

    admin_id = uuid.uuid4()
    hashed_password = hasher.hash(settings.admin_password)
    conn.execute(
        users_table.insert().values(  # type: ignore[attr-defined]
            id=admin_id,
            email=admin_email,
            password_hash=hashed_password,
            status="ACTIVE",
            email_verified_at=now,
            created_at=now,
            updated_at=now,
            mfa_enabled=False,
        )
    )

    role_id = conn.execute(
        sa.select(roles_table.c.id).where(roles_table.c.name == "ADMIN")  # type: ignore[attr-defined]
    ).scalar_one()

    user_roles_table = sa.table(
        "user_roles",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("user_id", postgresql.UUID(as_uuid=True)),
        sa.column("role_id", postgresql.UUID(as_uuid=True)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )

    conn.execute(
        user_roles_table.insert().values(  # type: ignore[attr-defined]
            id=uuid.uuid4(),
            user_id=admin_id,
            role_id=role_id,
            created_at=now,
            updated_at=now,
        )
    )
