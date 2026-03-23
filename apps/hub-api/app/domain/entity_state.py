from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.base import Base


class EntityState(Base):
    __tablename__ = "entity_state"

    entity_id: Mapped[str] = mapped_column(ForeignKey("entities.id"), primary_key=True)
    value_json: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(64))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False))
    version: Mapped[int] = mapped_column(Integer, default=1)
