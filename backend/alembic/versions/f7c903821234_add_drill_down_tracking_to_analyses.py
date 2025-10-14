"""add_drill_down_tracking_to_analyses

Revision ID: f7c903821234
Revises: 003_ssl_configuration
Create Date: 2025-10-13 13:25:20.709469

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f7c903821234'
down_revision = '003_ssl_configuration'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add drill-down tracking columns to analyses table
    op.add_column('analyses', sa.Column('parent_analysis_id', sa.Integer(), nullable=True))
    op.add_column('analyses', sa.Column('is_drill_down', sa.Boolean(), nullable=False, server_default='false'))

    # Add foreign key constraint
    op.create_foreign_key('fk_analyses_parent_analysis_id', 'analyses', 'analyses', ['parent_analysis_id'], ['id'], ondelete='SET NULL')

    # Add indexes for performance
    op.create_index('ix_analyses_parent_analysis_id', 'analyses', ['parent_analysis_id'])
    op.create_index('ix_analyses_is_drill_down', 'analyses', ['is_drill_down'])


def downgrade() -> None:
    # Remove indexes
    op.drop_index('ix_analyses_is_drill_down', 'analyses')
    op.drop_index('ix_analyses_parent_analysis_id', 'analyses')

    # Remove foreign key constraint
    op.drop_constraint('fk_analyses_parent_analysis_id', 'analyses', type_='foreignkey')

    # Remove columns
    op.drop_column('analyses', 'is_drill_down')
    op.drop_column('analyses', 'parent_analysis_id')
