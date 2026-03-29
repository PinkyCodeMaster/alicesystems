from __future__ import annotations

from datetime import UTC, datetime
import json

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.domain.device import Device
from app.domain.device_bootstrap_record import DeviceBootstrapRecord
from app.domain.device_credential import DeviceCredential
from app.domain.entity import Entity
from app.domain.entity_state import EntityState
from app.domain.provisioning_session import ProvisioningSession
from app.domain.user import User
from app.repositories.device_repository import DeviceRepository
from app.services.audit_service import AuditService


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class DeviceRemovalService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.device_repo = DeviceRepository(db)
        self.audit_service = AuditService(db)

    def remove(self, *, device_id: str, actor: User) -> str:
        device = self.device_repo.get_by_id(device_id)
        if device is None or device.site_id != actor.site_id:
            raise ValueError("Device not found.")

        now = _now()
        entities = list(self.db.scalars(select(Entity).where(Entity.device_id == device.id)))
        entity_ids = [entity.id for entity in entities]

        if entity_ids:
            self.db.execute(delete(EntityState).where(EntityState.entity_id.in_(entity_ids)))
            self.db.execute(delete(Entity).where(Entity.id.in_(entity_ids)))

        self.db.execute(delete(DeviceCredential).where(DeviceCredential.device_id == device.id))

        bootstrap_records = list(
            self.db.scalars(
                select(DeviceBootstrapRecord).where(DeviceBootstrapRecord.claimed_device_id == device.id)
            )
        )
        for record in bootstrap_records:
            record.status = "claimable"
            record.claimed_device_id = None
            record.claimed_at = None
            record.updated_at = now

        sessions = list(
            self.db.scalars(select(ProvisioningSession).where(ProvisioningSession.claimed_device_id == device.id))
        )
        for session in sessions:
            session.claimed_device_id = None
            session.updated_at = now

        self.db.execute(delete(Device).where(Device.id == device.id))
        self.db.commit()

        self.audit_service.record_event(
            site_id=actor.site_id,
            actor_type="user",
            actor_id=actor.id,
            action="device.removed",
            target_type="device",
            target_id=device.id,
            severity="warning",
            metadata_json=json.dumps(
                {
                    "device_name": device.name,
                    "entity_count": len(entity_ids),
                    "bootstrap_ids_reset": [record.id for record in bootstrap_records],
                }
            ),
        )
        return device.id
