"""Update storage quota defaults to 5000 MB

Revision ID: 006_update_quota_defaults
Revises: 005_add_user_invites
Create Date: 2025-10-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '006_update_quota_defaults'
down_revision = '005_add_user_invites'
branch_labels = None
depends_on = None


def _set_default(table_name, column_name, default_value):
    bind = op.get_bind()
    inspector = inspect(bind)
    if table_name not in inspector.get_table_names():
        return
    columns = {col['name'] for col in inspector.get_columns(table_name)}
    if column_name not in columns:
        return
    op.alter_column(
        table_name,
        column_name,
        existing_type=sa.Integer(),
        server_default=sa.text(str(default_value))
    )


def upgrade() -> None:
    _set_default('users', 'storage_quota_mb', 5000)
    _set_default('user_invites', 'storage_quota_mb', 5000)


def downgrade() -> None:
    _set_default('users', 'storage_quota_mb', 10240)
    _set_default('user_invites', 'storage_quota_mb', 500)
