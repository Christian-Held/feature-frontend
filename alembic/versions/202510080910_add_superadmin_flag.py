"""add_superadmin_flag

Revision ID: 202510080910
Revises: 202510080830
Create Date: 2025-10-08 09:10:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '202510080910'
down_revision = '202510080830'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_superadmin column to users table
    op.add_column('users', sa.Column('is_superadmin', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    op.drop_column('users', 'is_superadmin')
