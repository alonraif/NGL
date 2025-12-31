"""Add SMTP configuration table

Revision ID: 007_add_smtp_config
Revises: 006_update_quota_defaults
Create Date: 2025-10-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '007_add_smtp_config'
down_revision = '006_update_quota_defaults'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = inspector.get_table_names()

    if 'smtp_configurations' not in tables:
        op.create_table(
            'smtp_configurations',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('host', sa.String(length=255), nullable=True),
            sa.Column('port', sa.Integer(), nullable=True),
            sa.Column('username', sa.String(length=255), nullable=True),
            sa.Column('password', sa.String(length=255), nullable=True),
            sa.Column('from_email', sa.String(length=255), nullable=True),
            sa.Column('use_tls', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )

        print("✅ Created smtp_configurations table")
    else:
        print("⚠️  smtp_configurations table already exists, skipping")


def downgrade() -> None:
    op.drop_table('smtp_configurations')
