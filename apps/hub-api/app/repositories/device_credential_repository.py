from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.device_credential import DeviceCredential


class DeviceCredentialRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_device_id(self, device_id: str) -> DeviceCredential | None:
        stmt = select(DeviceCredential).where(DeviceCredential.device_id == device_id)
        return self.db.scalar(stmt)

    def save(self, credential: DeviceCredential) -> DeviceCredential:
        self.db.add(credential)
        self.db.commit()
        self.db.refresh(credential)
        return credential
