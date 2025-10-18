"""Add bookmarks table for shared analysis viewing

Revision ID: 004_add_bookmarks
Revises: 003_ssl_configuration
Create Date: 2025-10-18

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '004_add_bookmarks'
down_revision = 'f7c903821234'  # Depends on drill-down tracking
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    # Check if bookmarks table exists
    tables = inspector.get_table_names()

    if 'bookmarks' not in tables:
        # Create bookmarks table
        op.create_table(
            'bookmarks',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('analysis_id', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['analysis_id'], ['analyses.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )

        # Create indexes
        op.create_index('idx_user_analysis_bookmark', 'bookmarks', ['user_id', 'analysis_id'], unique=True)
        op.create_index(op.f('ix_bookmarks_created_at'), 'bookmarks', ['created_at'], unique=False)

        print("✅ Created bookmarks table with indexes")
    else:
        print("⚠️  Bookmarks table already exists, skipping")


def downgrade() -> None:
    # Drop table (cascades will handle foreign keys)
    op.drop_table('bookmarks')
