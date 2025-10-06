"""Add S3 configuration and storage_type to log_files

Revision ID: 002_add_s3_configuration
Revises: 001_add_session_fields
Create Date: 2025-10-06

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_add_s3_configuration'
down_revision = '001_add_session_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create s3_configurations table
    op.create_table(
        's3_configurations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('aws_access_key_id', sa.String(length=255), nullable=False),
        sa.Column('aws_secret_access_key', sa.String(length=255), nullable=False),
        sa.Column('bucket_name', sa.String(length=255), nullable=False),
        sa.Column('region', sa.String(length=50), nullable=False),
        sa.Column('server_side_encryption', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('last_test_success', sa.Boolean(), nullable=True),
        sa.Column('last_test_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_test_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Add storage_type column to log_files (default 'local')
    op.add_column('log_files', sa.Column('storage_type', sa.String(length=20), nullable=True, server_default='local'))

    # Update existing rows to have 'local' storage type
    op.execute("UPDATE log_files SET storage_type = 'local' WHERE storage_type IS NULL")

    # Make storage_type NOT NULL
    op.alter_column('log_files', 'storage_type', nullable=False)


def downgrade() -> None:
    # Drop storage_type column from log_files
    op.drop_column('log_files', 'storage_type')

    # Drop s3_configurations table
    op.drop_table('s3_configurations')
