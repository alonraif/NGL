"""Add SSL configuration support

Revision ID: 003_ssl_configuration
Revises: 002_add_s3_configuration
Create Date: 2025-10-07

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_ssl_configuration'
down_revision = '002_add_s3_configuration'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ssl_configurations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('mode', sa.String(length=20), nullable=False, server_default='lets_encrypt'),
        sa.Column('primary_domain', sa.String(length=255), nullable=True),
        sa.Column('alternate_domains', sa.JSON(), nullable=True),
        sa.Column('enforce_https', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('certificate_status', sa.String(length=50), nullable=False, server_default='idle'),
        sa.Column('last_issued_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('verification_hostname', sa.String(length=255), nullable=True),
        sa.Column('uploaded_certificate_path', sa.String(length=512), nullable=True),
        sa.Column('uploaded_private_key_path', sa.String(length=512), nullable=True),
        sa.Column('uploaded_chain_path', sa.String(length=512), nullable=True),
        sa.Column('uploaded_fingerprint', sa.String(length=128), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('auto_renew', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('ssl_configurations')
