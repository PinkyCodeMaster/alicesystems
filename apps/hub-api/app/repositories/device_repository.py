from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.device import Device


class DeviceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_all(self) -> list[Device]:
        return list(self.db.scalars(select(Device).order_by(Device.name)))

    def get_by_id(self, device_id: str) -> Device | None:
        stmt = select(Device).where(Device.id == device_id)
        return self.db.scalar(stmt)

    def save(self, device: Device) -> Device:
        self.db.add(device)
        self.db.commit()
        self.db.refresh(device)
        return device
