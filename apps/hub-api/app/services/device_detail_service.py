from __future__ import annotations

import json

from app.repositories.room_repository import RoomRepository
from app.repositories.entity_repository import EntityRepository
from app.repositories.entity_state_repository import EntityStateRepository
from app.schemas.audit import AuditEventListItem
from app.schemas.devices import DeviceDetailEntityItem, DeviceDetailResponse, DeviceListItem
from app.services.audit_service import AuditService
from app.services.device_registry_service import DeviceRegistryService
from sqlalchemy.orm import Session


class DeviceDetailService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.device_registry = DeviceRegistryService(db)
        self.entity_repo = EntityRepository(db)
        self.state_repo = EntityStateRepository(db)
        self.room_repo = RoomRepository(db)
        self.audit_service = AuditService(db)

    def get(self, *, device_id: str) -> DeviceDetailResponse | None:
        device = self.device_registry.get_device(device_id)
        if device is None:
            return None
        room = self.room_repo.get_by_id(device.room_id) if device.room_id else None

        entities = self.entity_repo.list_by_device(device_id)
        states = {
            state.entity_id: state
            for state in self.state_repo.list_by_entity_ids([entity.id for entity in entities])
        }
        audit_items = [
            AuditEventListItem.model_validate(event)
            for event in self.audit_service.list_recent_for_target(target_id=device_id, limit=20)
        ]
        for entity in entities:
            audit_items.extend(
                AuditEventListItem.model_validate(event)
                for event in self.audit_service.list_recent_for_target(target_id=entity.id, limit=20)
            )
        audit_items.sort(key=lambda item: item.created_at, reverse=True)
        deduped: list[AuditEventListItem] = []
        seen_ids: set[str] = set()
        for item in audit_items:
            if item.id in seen_ids:
                continue
            seen_ids.add(item.id)
            deduped.append(item)
            if len(deduped) >= 20:
                break

        return DeviceDetailResponse(
            device=DeviceListItem(
                id=device.id,
                site_id=device.site_id,
                room_id=device.room_id,
                room_name=room.name if room is not None else None,
                name=device.name,
                model=device.model,
                device_type=device.device_type,
                protocol=device.protocol,
                status=device.status,
                provisioning_status=device.provisioning_status,
                fw_version=device.fw_version,
                mqtt_client_id=device.mqtt_client_id,
                last_seen_at=device.last_seen_at,
            ),
            entities=[
                DeviceDetailEntityItem(
                    id=entity.id,
                    room_id=entity.room_id,
                    capability_id=entity.capability_id,
                    kind=entity.kind,
                    name=entity.name,
                    writable=entity.writable,
                    traits_json=entity.traits_json,
                    state=json.loads(states[entity.id].value_json) if entity.id in states else None,
                    state_source=states[entity.id].source if entity.id in states else None,
                    state_updated_at=states[entity.id].updated_at if entity.id in states else None,
                    state_version=states[entity.id].version if entity.id in states else None,
                )
                for entity in entities
            ],
            audit_events=deduped,
        )
