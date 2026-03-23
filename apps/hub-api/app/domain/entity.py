from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.base import Base


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    site_id: Mapped[str] = mapped_column(ForeignKey("sites.id"), index=True)
    room_id: Mapped[str | None] = mapped_column(ForeignKey("rooms.id"), nullable=True, index=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), index=True)
    capability_id: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), index=True)
    writable: Mapped[int] = mapped_column(Integer, default=0)
    traits_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False))
