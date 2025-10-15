"""add_drill_down_tracking_to_analyses

Revision ID: f7c903821234
Revises: 003_ssl_configuration
Create Date: 2025-10-13 13:25:20.709469

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'f7c903821234'
down_revision = '003_ssl_configuration'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {col['name'] for col in inspector.get_columns('analyses')}
    indexes = {idx['name'] for idx in inspector.get_indexes('analyses')}
    fk_names = {fk['name'] for fk in inspector.get_foreign_keys('analyses') if fk.get('name')}

    # Add drill-down tracking columns to analyses table
    if 'parent_analysis_id' not in columns:
        op.add_column('analyses', sa.Column('parent_analysis_id', sa.Integer(), nullable=True))
        columns.add('parent_analysis_id')

    if 'is_drill_down' not in columns:
        op.add_column('analyses', sa.Column('is_drill_down', sa.Boolean(), nullable=False, server_default='false'))
        # Ensure default conforms to application expectation
        op.execute("UPDATE analyses SET is_drill_down = FALSE WHERE is_drill_down IS NULL")
        op.alter_column('analyses', 'is_drill_down', server_default='false', nullable=False)

    # Add foreign key constraint
    if 'fk_analyses_parent_analysis_id' not in fk_names and 'parent_analysis_id' in columns:
        op.create_foreign_key(
            'fk_analyses_parent_analysis_id',
            'analyses',
            'analyses',
            ['parent_analysis_id'],
            ['id'],
            ondelete='SET NULL'
        )

    # Add indexes for performance
    if 'parent_analysis_id' in columns and 'ix_analyses_parent_analysis_id' not in indexes:
        op.create_index('ix_analyses_parent_analysis_id', 'analyses', ['parent_analysis_id'])

    if 'is_drill_down' in columns and 'ix_analyses_is_drill_down' not in indexes:
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
