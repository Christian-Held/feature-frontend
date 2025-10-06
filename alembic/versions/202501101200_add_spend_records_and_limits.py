"""Add spend records table and widen spend limit precision."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202501101200"
down_revision = "202410091200"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "spend_limits",
        "monthly_cap_usd",
        existing_type=sa.Numeric(10, 2),
        type_=sa.Numeric(12, 2),
        existing_nullable=False,
    )

    op.create_table(
        "spend_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount_usd", sa.Numeric(12, 2), nullable=False),
        sa.Column("metadata", sa.JSON()),
    )
    op.create_index("ix_spend_records_user_month", "spend_records", ["user_id", "created_at"])

    plans_table = sa.table(
        "plans",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("monthly_price_usd", sa.Numeric(10, 2)),
        sa.column("metadata", sa.JSON()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )

    conn = op.get_bind()
    existing_codes = {row[0] for row in conn.execute(sa.select(plans_table.c.code))}
    now = datetime.now(timezone.utc)
    seed_data = []
    if "FREE" not in existing_codes:
        seed_data.append({
            "id": uuid.uuid4(),
            "code": "FREE",
            "name": "Free",
            "monthly_price_usd": 0,
            "metadata": {"features": ["Basic usage", "Community support"]},
            "created_at": now,
            "updated_at": now,
        })
    if "PRO" not in existing_codes:
        seed_data.append({
            "id": uuid.uuid4(),
            "code": "PRO",
            "name": "Pro",
            "monthly_price_usd": 99,
            "metadata": {"features": ["Priority queue", "Usage analytics", "Premium support"]},
            "created_at": now,
            "updated_at": now,
        })

    for row in seed_data:
        conn.execute(plans_table.insert().values(**row))


def downgrade() -> None:
    op.drop_index("ix_spend_records_user_month", table_name="spend_records")
    op.drop_table("spend_records")
    op.alter_column(
        "spend_limits",
        "monthly_cap_usd",
        existing_type=sa.Numeric(12, 2),
        type_=sa.Numeric(10, 2),
        existing_nullable=False,
    )
