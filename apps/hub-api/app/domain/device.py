from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.base import Base


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    site_id: Mapped[str] = mapped_column(ForeignKey("sites.id"), index=True)
    room_id: Mapped[str | None] = mapped_column(ForeignKey("rooms.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    model: Mapped[str] = mapped_column(String(128))
    device_type: Mapped[str] = mapped_column(String(64))
    protocol: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="offline")
    provisioning_status: Mapped[str] = mapped_column(String(32), default="unprovisioned")
    fw_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mqtt_client_id: Mapped[str] = mapped_column(String(128), unique=True)
    capability_descriptor_json: Mapped[str] = mapped_column(Text, default="{}")
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False))
