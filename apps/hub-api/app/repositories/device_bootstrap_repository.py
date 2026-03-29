from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.device_bootstrap_record import DeviceBootstrapRecord


class DeviceBootstrapRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_all(self) -> list[DeviceBootstrapRecord]:
        return list(self.db.scalars(select(DeviceBootstrapRecord).order_by(DeviceBootstrapRecord.id)))

    def get_by_id(self, bootstrap_id: str) -> DeviceBootstrapRecord | None:
        stmt = select(DeviceBootstrapRecord).where(DeviceBootstrapRecord.id == bootstrap_id)
        return self.db.scalar(stmt)

    def save(self, record: DeviceBootstrapRecord) -> DeviceBootstrapRecord:
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record
