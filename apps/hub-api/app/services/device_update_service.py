from __future__ import annotations

from datetime import UTC, datetime
import json
import re

from sqlalchemy.orm import Session

from app.domain.device import Device
from app.repositories.device_repository import DeviceRepository
from app.repositories.entity_repository import EntityRepository
from app.repositories.room_repository import RoomRepository
from app.services.audit_service import AuditService


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _slugify(value: str) -> str:
    value = value.strip().lower()
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


class DeviceUpdateService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.device_repo = DeviceRepository(db)
        self.entity_repo = EntityRepository(db)
        self.room_repo = RoomRepository(db)
        self.audit_service = AuditService(db)

    def update_metadata(
        self,
        *,
        device_id: str,
        name: str,
        room_id: str | None,
        actor_id: str,
    ) -> Device:
        device = self.device_repo.get_by_id(device_id)
        if device is None:
            raise ValueError("Device not found")

        cleaned_name = name.strip()
        if not cleaned_name:
            raise ValueError("Device name is required")

        if room_id is not None and self.room_repo.get_by_id(room_id) is None:
            raise ValueError("Room not found")

        previous_name = device.name
        previous_room_id = device.room_id
        now = _now()

        device.name = cleaned_name
        device.room_id = room_id
        device.updated_at = now
        self.db.add(device)

        old_slug = _slugify(previous_name)
        new_slug = _slugify(cleaned_name)
        for entity in self.entity_repo.list_by_device(device_id):
            entity.room_id = room_id
            if entity.name == previous_name:
                entity.name = cleaned_name
            elif entity.name.startswith(f"{previous_name} "):
                entity.name = f"{cleaned_name}{entity.name.removeprefix(previous_name)}"

            if entity.slug == old_slug:
                entity.slug = new_slug
            elif entity.slug.startswith(f"{old_slug}-"):
                entity.slug = f"{new_slug}{entity.slug.removeprefix(old_slug)}"

            entity.updated_at = now
            self.db.add(entity)

        self.db.commit()
        self.db.refresh(device)

        self.audit_service.record_event(
            site_id=device.site_id,
            actor_type="user",
            actor_id=actor_id,
            action="device.metadata_updated",
            target_type="device",
            target_id=device.id,
            severity="info",
            metadata_json=json.dumps(
                {
                    "name": device.name,
                    "room_id": device.room_id,
                    "previous_name": previous_name,
                    "previous_room_id": previous_room_id,
                }
            ),
        )
        return device
