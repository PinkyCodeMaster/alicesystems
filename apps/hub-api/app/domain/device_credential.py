from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.base import Base


class DeviceCredential(Base):
    __tablename__ = "device_credentials"

    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), primary_key=True)
    mqtt_username: Mapped[str] = mapped_column(String(128), unique=True)
    mqtt_password_hash: Mapped[str] = mapped_column(String(255))
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=False))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False))
