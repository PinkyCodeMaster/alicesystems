from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.base import Base


class DeviceBootstrapRecord(Base):
    __tablename__ = "device_bootstrap_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    model: Mapped[str] = mapped_column(String(128))
    device_type: Mapped[str] = mapped_column(String(64))
    hardware_revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    default_device_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    setup_code_hash: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="claimable")
    claimed_device_id: Mapped[str | None] = mapped_column(ForeignKey("devices.id"), nullable=True, index=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False))
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
