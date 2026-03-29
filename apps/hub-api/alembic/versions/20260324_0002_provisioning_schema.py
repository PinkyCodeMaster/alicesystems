"""Provisioning schema.

Revision ID: 20260324_0002
Revises: 20260323_0002
Create Date: 2026-03-24 16:05:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260324_0002"
down_revision = "20260323_0002"
branch_labels = None
depends_on = None


def _table_names() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    tables = _table_names()

    if "device_bootstrap_records" not in tables:
        op.create_table(
            "device_bootstrap_records",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("model", sa.String(length=128), nullable=False),
            sa.Column("device_type", sa.String(length=64), nullable=False),
            sa.Column("hardware_revision", sa.String(length=64), nullable=True),
            sa.Column("default_device_id", sa.String(length=64), nullable=True),
            sa.Column("setup_code_hash", sa.String(length=255), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("claimed_device_id", sa.String(length=64), sa.ForeignKey("devices.id"), nullable=True),
            sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("claimed_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("default_device_id", name="uq_device_bootstrap_records_default_device_id"),
        )
        op.create_index(
            "ix_device_bootstrap_records_claimed_device_id",
            "device_bootstrap_records",
            ["claimed_device_id"],
        )

    if "provisioning_sessions" not in tables:
        op.create_table(
            "provisioning_sessions",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("site_id", sa.String(length=64), sa.ForeignKey("sites.id"), nullable=False),
            sa.Column("created_by_user_id", sa.String(length=64), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("bootstrap_id", sa.String(length=64), sa.ForeignKey("device_bootstrap_records.id"), nullable=False),
            sa.Column("room_id", sa.String(length=64), sa.ForeignKey("rooms.id"), nullable=True),
            sa.Column("requested_device_name", sa.String(length=255), nullable=True),
            sa.Column("claim_token_hash", sa.String(length=255), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("claimed_device_id", sa.String(length=64), sa.ForeignKey("devices.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_provisioning_sessions_site_id", "provisioning_sessions", ["site_id"])
        op.create_index("ix_provisioning_sessions_created_by_user_id", "provisioning_sessions", ["created_by_user_id"])
        op.create_index("ix_provisioning_sessions_bootstrap_id", "provisioning_sessions", ["bootstrap_id"])
        op.create_index("ix_provisioning_sessions_room_id", "provisioning_sessions", ["room_id"])
        op.create_index("ix_provisioning_sessions_claimed_device_id", "provisioning_sessions", ["claimed_device_id"])

    if "device_credentials" not in tables:
        op.create_table(
            "device_credentials",
            sa.Column("device_id", sa.String(length=64), sa.ForeignKey("devices.id"), primary_key=True),
            sa.Column("mqtt_username", sa.String(length=128), nullable=False),
            sa.Column("mqtt_password_hash", sa.String(length=255), nullable=False),
            sa.Column("issued_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("mqtt_username", name="uq_device_credentials_mqtt_username"),
        )


def downgrade() -> None:
    tables = _table_names()

    if "device_credentials" in tables:
        op.drop_table("device_credentials")
    if "provisioning_sessions" in tables:
        op.drop_index("ix_provisioning_sessions_claimed_device_id", table_name="provisioning_sessions")
        op.drop_index("ix_provisioning_sessions_room_id", table_name="provisioning_sessions")
        op.drop_index("ix_provisioning_sessions_bootstrap_id", table_name="provisioning_sessions")
        op.drop_index("ix_provisioning_sessions_created_by_user_id", table_name="provisioning_sessions")
        op.drop_index("ix_provisioning_sessions_site_id", table_name="provisioning_sessions")
        op.drop_table("provisioning_sessions")
    if "device_bootstrap_records" in tables:
        op.drop_index("ix_device_bootstrap_records_claimed_device_id", table_name="device_bootstrap_records")
        op.drop_table("device_bootstrap_records")
