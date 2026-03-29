from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.base import Base


class ProvisioningSession(Base):
    __tablename__ = "provisioning_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    site_id: Mapped[str] = mapped_column(ForeignKey("sites.id"), index=True)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    bootstrap_id: Mapped[str] = mapped_column(ForeignKey("device_bootstrap_records.id"), index=True)
    room_id: Mapped[str | None] = mapped_column(ForeignKey("rooms.id"), nullable=True, index=True)
    requested_device_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    claim_token_hash: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=False))
    claimed_device_id: Mapped[str | None] = mapped_column(ForeignKey("devices.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
