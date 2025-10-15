"""Add session_name and zendesk_case to analyses

Revision ID: 001_add_session_fields
Revises:
Create Date: 2025-10-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '001_add_session_fields'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {col['name'] for col in inspector.get_columns('analyses')}
    indexes = {idx['name'] for idx in inspector.get_indexes('analyses')}

    # Add session_name column (NOT NULL with a default for existing rows)
    if 'session_name' not in columns:
        op.add_column('analyses', sa.Column('session_name', sa.String(length=255), nullable=True))
        columns.add('session_name')

    if 'zendesk_case' not in columns:
        op.add_column('analyses', sa.Column('zendesk_case', sa.String(length=100), nullable=True))
        columns.add('zendesk_case')

    if 'session_name' in columns:
        # Update existing rows with a default session name based on filename
        op.execute("""
            UPDATE analyses
            SET session_name =
                CASE
                    WHEN log_files.original_filename IS NOT NULL
                    THEN CONCAT('Analysis ', analyses.id, ' - ', log_files.original_filename)
                    ELSE CONCAT('Analysis ', analyses.id)
                END
            FROM log_files
            WHERE analyses.log_file_id = log_files.id
              AND analyses.session_name IS NULL
        """)

        # Update any remaining rows without a log_file
        op.execute("""
            UPDATE analyses
            SET session_name = CONCAT('Analysis ', id)
            WHERE session_name IS NULL
        """)

        # Now make session_name NOT NULL
        op.alter_column('analyses', 'session_name', nullable=False)

    # Create indexes if missing
    if 'session_name' in columns and op.f('ix_analyses_session_name') not in indexes:
        op.create_index(op.f('ix_analyses_session_name'), 'analyses', ['session_name'], unique=False)

    if 'zendesk_case' in columns and op.f('ix_analyses_zendesk_case') not in indexes:
        op.create_index(op.f('ix_analyses_zendesk_case'), 'analyses', ['zendesk_case'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_analyses_zendesk_case'), table_name='analyses')
    op.drop_index(op.f('ix_analyses_session_name'), table_name='analyses')

    # Drop columns
    op.drop_column('analyses', 'zendesk_case')
    op.drop_column('analyses', 'session_name')
