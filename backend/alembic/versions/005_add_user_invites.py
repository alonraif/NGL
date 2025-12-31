"""Add user_invites table

Revision ID: 005_add_user_invites
Revises: 004_add_bookmarks
Create Date: 2025-10-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '005_add_user_invites'
down_revision = '004_add_bookmarks'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = inspector.get_table_names()

    if 'user_invites' not in tables:
        op.create_table(
            'user_invites',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('email', sa.String(length=255), nullable=False),
            sa.Column('username', sa.String(length=50), nullable=False),
            sa.Column('role', sa.String(length=20), nullable=False, server_default='user'),
            sa.Column('storage_quota_mb', sa.Integer(), nullable=True),
            sa.Column('token_hash', sa.String(length=64), nullable=False),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_by', sa.Integer(), nullable=True),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )

        op.create_index(op.f('ix_user_invites_email'), 'user_invites', ['email'], unique=False)
        op.create_index(op.f('ix_user_invites_expires_at'), 'user_invites', ['expires_at'], unique=False)
        op.create_index(op.f('ix_user_invites_token_hash'), 'user_invites', ['token_hash'], unique=True)

        print("✅ Created user_invites table with indexes")
    else:
        print("⚠️  user_invites table already exists, skipping")


def downgrade() -> None:
    op.drop_table('user_invites')
