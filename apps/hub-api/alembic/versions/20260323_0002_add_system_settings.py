"""Add system settings table.

Revision ID: 20260323_0002
Revises: 20260323_0001
Create Date: 2026-03-23 17:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260323_0002"
down_revision = "20260323_0001"
branch_labels = None
depends_on = None


def _table_names() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if "system_settings" in _table_names():
        return

    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(length=128), primary_key=True),
        sa.Column("site_id", sa.String(length=64), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("value_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_system_settings_site_id", "system_settings", ["site_id"])


def downgrade() -> None:
    if "system_settings" not in _table_names():
        return

    op.drop_index("ix_system_settings_site_id", table_name="system_settings")
    op.drop_table("system_settings")
