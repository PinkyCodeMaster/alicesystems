"""Initial canonical schema.

Revision ID: 20260323_0001
Revises:
Create Date: 2026-03-23 13:20:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260323_0001"
down_revision = None
branch_labels = None
depends_on = None


def _table_names() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def _create_sites() -> None:
    op.create_table(
        "sites",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def _create_users() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("site_id", sa.String(length=64), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_site_id", "users", ["site_id"])


def _create_rooms() -> None:
    op.create_table(
        "rooms",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("site_id", sa.String(length=64), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_rooms_site_id", "rooms", ["site_id"])
    op.create_index("ix_rooms_slug", "rooms", ["slug"])


def _create_devices() -> None:
    op.create_table(
        "devices",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("site_id", sa.String(length=64), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("room_id", sa.String(length=64), sa.ForeignKey("rooms.id"), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("device_type", sa.String(length=64), nullable=False),
        sa.Column("protocol", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("provisioning_status", sa.String(length=32), nullable=False),
        sa.Column("fw_version", sa.String(length=64), nullable=True),
        sa.Column("mqtt_client_id", sa.String(length=128), nullable=False),
        sa.Column("capability_descriptor_json", sa.Text(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("mqtt_client_id", name="uq_devices_mqtt_client_id"),
    )
    op.create_index("ix_devices_site_id", "devices", ["site_id"])
    op.create_index("ix_devices_room_id", "devices", ["room_id"])


def _create_entities() -> None:
    op.create_table(
        "entities",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("site_id", sa.String(length=64), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("room_id", sa.String(length=64), sa.ForeignKey("rooms.id"), nullable=True),
        sa.Column("device_id", sa.String(length=64), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("capability_id", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("writable", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("traits_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_entities_site_id", "entities", ["site_id"])
    op.create_index("ix_entities_room_id", "entities", ["room_id"])
    op.create_index("ix_entities_device_id", "entities", ["device_id"])
    op.create_index("ix_entities_slug", "entities", ["slug"])


def _create_entity_state() -> None:
    op.create_table(
        "entity_state",
        sa.Column("entity_id", sa.String(length=64), sa.ForeignKey("entities.id"), primary_key=True),
        sa.Column("value_json", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )


def _create_audit_events() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("site_id", sa.String(length=64), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("actor_type", sa.String(length=64), nullable=False),
        sa.Column("actor_id", sa.String(length=64), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_audit_events_site_id", "audit_events", ["site_id"])


def upgrade() -> None:
    tables = _table_names()

    if "sites" not in tables:
        _create_sites()
        tables.add("sites")
    if "users" not in tables:
        _create_users()
        tables.add("users")
    if "rooms" not in tables:
        _create_rooms()
        tables.add("rooms")
    if "devices" not in tables:
        _create_devices()
        tables.add("devices")
    if "entities" not in tables:
        _create_entities()
        tables.add("entities")
    if "entity_state" not in tables:
        _create_entity_state()
        tables.add("entity_state")
    if "audit_events" not in tables:
        _create_audit_events()


def downgrade() -> None:
    tables = _table_names()

    if "audit_events" in tables:
        op.drop_index("ix_audit_events_site_id", table_name="audit_events")
        op.drop_table("audit_events")
    if "entity_state" in tables:
        op.drop_table("entity_state")
    if "entities" in tables:
        op.drop_index("ix_entities_slug", table_name="entities")
        op.drop_index("ix_entities_device_id", table_name="entities")
        op.drop_index("ix_entities_room_id", table_name="entities")
        op.drop_index("ix_entities_site_id", table_name="entities")
        op.drop_table("entities")
    if "devices" in tables:
        op.drop_index("ix_devices_room_id", table_name="devices")
        op.drop_index("ix_devices_site_id", table_name="devices")
        op.drop_table("devices")
    if "rooms" in tables:
        op.drop_index("ix_rooms_slug", table_name="rooms")
        op.drop_index("ix_rooms_site_id", table_name="rooms")
        op.drop_table("rooms")
    if "users" in tables:
        op.drop_index("ix_users_site_id", table_name="users")
        op.drop_table("users")
    if "sites" in tables:
        op.drop_table("sites")
