"""rename audit event metadata column

Revision ID: 202510081530
Revises: 202510081500
Create Date: 2025-10-08 15:30:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "202510081530"
down_revision = "202510081500"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("audit_events", "metadata", new_column_name="event_metadata")


def downgrade() -> None:
    op.alter_column("audit_events", "event_metadata", new_column_name="metadata")
