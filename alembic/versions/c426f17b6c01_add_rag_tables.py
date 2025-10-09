"""Add RAG tables

Revision ID: c426f17b6c01
Revises: 202510081530
Create Date: 2025-10-08 20:43:41

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c426f17b6c01'
down_revision = '202510081530'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types using postgresql.ENUM with create_type=False to prevent auto-creation
    website_status_enum = postgresql.ENUM('PENDING', 'CRAWLING', 'READY', 'ERROR', 'PAUSED', name='website_status', create_type=False)
    chatbot_position_enum = postgresql.ENUM('BOTTOM_RIGHT', 'BOTTOM_LEFT', 'TOP_RIGHT', 'TOP_LEFT', name='chatbot_position', create_type=False)
    crawl_frequency_enum = postgresql.ENUM('MANUAL', 'DAILY', 'WEEKLY', 'MONTHLY', name='crawl_frequency', create_type=False)

    # Manually create enum types with proper error handling
    conn = op.get_bind()
    conn.execute(sa.text("DO $$ BEGIN CREATE TYPE website_status AS ENUM ('PENDING', 'CRAWLING', 'READY', 'ERROR', 'PAUSED'); EXCEPTION WHEN duplicate_object THEN null; END $$;"))
    conn.execute(sa.text("DO $$ BEGIN CREATE TYPE chatbot_position AS ENUM ('BOTTOM_RIGHT', 'BOTTOM_LEFT', 'TOP_RIGHT', 'TOP_LEFT'); EXCEPTION WHEN duplicate_object THEN null; END $$;"))
    conn.execute(sa.text("DO $$ BEGIN CREATE TYPE crawl_frequency AS ENUM ('MANUAL', 'DAILY', 'WEEKLY', 'MONTHLY'); EXCEPTION WHEN duplicate_object THEN null; END $$;"))

    # Create rag_websites table
    op.create_table('rag_websites',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('url', sa.String(length=2048), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('status', website_status_enum, nullable=False),
        sa.Column('embed_token', sa.String(length=64), nullable=False),
        sa.Column('brand_color', sa.String(length=7), nullable=True),
        sa.Column('logo_url', sa.String(length=2048), nullable=True),
        sa.Column('welcome_message', sa.Text(), nullable=True),
        sa.Column('position', chatbot_position_enum, nullable=False),
        sa.Column('language', sa.String(length=10), nullable=True),
        sa.Column('crawl_frequency', crawl_frequency_enum, nullable=False),
        sa.Column('max_pages', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('last_crawled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('pages_indexed', sa.Integer(), nullable=False),
        sa.Column('crawl_error', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('embed_token')
    )
    op.create_index('ix_rag_websites_embed_token', 'rag_websites', ['embed_token'], unique=False)
    op.create_index('ix_rag_websites_status', 'rag_websites', ['status'], unique=False)
    op.create_index('ix_rag_websites_user_id', 'rag_websites', ['user_id'], unique=False)

    # Create rag_website_pages table
    op.create_table('rag_website_pages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('website_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('url', sa.String(length=2048), nullable=False),
        sa.Column('title', sa.String(length=512), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('page_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('embedding_ids', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('last_crawled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(['website_id'], ['rag_websites.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_rag_website_pages_url', 'rag_website_pages', ['url'], unique=False)
    op.create_index('ix_rag_website_pages_website_id', 'rag_website_pages', ['website_id'], unique=False)

    # Create rag_custom_qas table
    op.create_table('rag_custom_qas',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('website_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('keywords', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['website_id'], ['rag_websites.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_rag_custom_qas_website_id', 'rag_custom_qas', ['website_id'], unique=False)

    # Create rag_conversations table
    op.create_table('rag_conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('website_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('visitor_id', sa.String(length=255), nullable=True),
        sa.Column('visitor_ip', sa.String(length=45), nullable=True),
        sa.Column('visitor_user_agent', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('messages', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('satisfaction_rating', sa.Integer(), nullable=True),
        sa.Column('feedback_text', sa.Text(), nullable=True),
        sa.Column('total_tokens', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['website_id'], ['rag_websites.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_rag_conversations_visitor_id', 'rag_conversations', ['visitor_id'], unique=False)
    op.create_index('ix_rag_conversations_website_id', 'rag_conversations', ['website_id'], unique=False)

    # Create rag_usage_stats table
    op.create_table('rag_usage_stats',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('website_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('conversations_count', sa.Integer(), nullable=False),
        sa.Column('messages_count', sa.Integer(), nullable=False),
        sa.Column('tokens_used', sa.Integer(), nullable=False),
        sa.Column('cost_usd', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('avg_satisfaction_rating', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('total_ratings', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['website_id'], ['rag_websites.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('website_id', 'date', name='uix_website_date')
    )
    op.create_index('ix_rag_usage_stats_date', 'rag_usage_stats', ['date'], unique=False)
    op.create_index('ix_rag_usage_stats_website_id', 'rag_usage_stats', ['website_id'], unique=False)

    # Add missing indexes to audit_events
    op.create_index('ix_audit_events_action', 'audit_events', ['action'], unique=False)
    op.create_index('ix_audit_events_created_at', 'audit_events', ['created_at'], unique=False)
    op.create_index('ix_audit_events_resource_id', 'audit_events', ['resource_id'], unique=False)
    op.create_index('ix_audit_events_resource_type', 'audit_events', ['resource_type'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_audit_events_resource_type', table_name='audit_events')
    op.drop_index('ix_audit_events_resource_id', table_name='audit_events')
    op.drop_index('ix_audit_events_created_at', table_name='audit_events')
    op.drop_index('ix_audit_events_action', table_name='audit_events')
    op.drop_index('ix_rag_usage_stats_website_id', table_name='rag_usage_stats')
    op.drop_index('ix_rag_usage_stats_date', table_name='rag_usage_stats')
    op.drop_index('ix_rag_conversations_website_id', table_name='rag_conversations')
    op.drop_index('ix_rag_conversations_visitor_id', table_name='rag_conversations')
    op.drop_index('ix_rag_custom_qas_website_id', table_name='rag_custom_qas')
    op.drop_index('ix_rag_website_pages_website_id', table_name='rag_website_pages')
    op.drop_index('ix_rag_website_pages_url', table_name='rag_website_pages')
    op.drop_index('ix_rag_websites_user_id', table_name='rag_websites')
    op.drop_index('ix_rag_websites_status', table_name='rag_websites')
    op.drop_index('ix_rag_websites_embed_token', table_name='rag_websites')

    # Drop tables
    op.drop_table('rag_usage_stats')
    op.drop_table('rag_conversations')
    op.drop_table('rag_custom_qas')
    op.drop_table('rag_website_pages')
    op.drop_table('rag_websites')

    # Drop enum types
    op.execute('DROP TYPE crawl_frequency')
    op.execute('DROP TYPE chatbot_position')
    op.execute('DROP TYPE website_status')
