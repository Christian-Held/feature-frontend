"""add_audit_events_table

Revision ID: 202510081500
Revises: 202510081400
Create Date: 2025-10-08 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '202510081500'
down_revision = '202510081400'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create audit_events table
    op.create_table(
        'audit_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=True),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('idx_audit_events_actor_id', 'audit_events', ['actor_id'])
    op.create_index('idx_audit_events_action', 'audit_events', ['action'])
    op.create_index('idx_audit_events_resource', 'audit_events', ['resource_type', 'resource_id'])
    op.create_index('idx_audit_events_created_at', 'audit_events', ['created_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_audit_events_created_at', table_name='audit_events')
    op.drop_index('idx_audit_events_resource', table_name='audit_events')
    op.drop_index('idx_audit_events_action', table_name='audit_events')
    op.drop_index('idx_audit_events_actor_id', table_name='audit_events')

    # Drop table
    op.drop_table('audit_events')
