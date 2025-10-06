"""Initial schema: api_keys and rate_limit_tracking tables

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create api_keys table
    op.create_table(
        'api_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('requests_count', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key', name='uq_api_keys_key')
    )
    op.create_index('ix_api_keys_key', 'api_keys', ['key'], unique=True)
    op.create_index('ix_api_keys_is_active', 'api_keys', ['is_active'])
    
    # Create rate_limit_tracking table
    op.create_table(
        'rate_limit_tracking',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('api_key', sa.String(length=64), nullable=False),
        sa.Column('endpoint', sa.String(length=200), nullable=False),
        sa.Column('window_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('window_type', sa.String(length=10), nullable=False),  # 'minute', 'hour', 'day'
        sa.Column('request_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_request_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_rate_limit_api_key', 'rate_limit_tracking', ['api_key'])
    op.create_index('ix_rate_limit_window', 'rate_limit_tracking', ['window_start', 'window_type'])
    op.create_index(
        'ix_rate_limit_lookup',
        'rate_limit_tracking',
        ['api_key', 'endpoint', 'window_start', 'window_type'],
        unique=False
    )


def downgrade() -> None:
    # Drop rate_limit_tracking table
    op.drop_index('ix_rate_limit_lookup', table_name='rate_limit_tracking')
    op.drop_index('ix_rate_limit_window', table_name='rate_limit_tracking')
    op.drop_index('ix_rate_limit_api_key', table_name='rate_limit_tracking')
    op.drop_table('rate_limit_tracking')
    
    # Drop api_keys table
    op.drop_index('ix_api_keys_is_active', table_name='api_keys')
    op.drop_index('ix_api_keys_key', table_name='api_keys')
    op.drop_table('api_keys')
