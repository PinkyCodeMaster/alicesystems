from __future__ import annotations

from datetime import UTC, datetime
import json
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.mqtt import publish_json
from app.repositories.device_repository import DeviceRepository
from app.repositories.entity_repository import EntityRepository
from app.services.audit_service import AuditService


class CommandService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.entity_repo = EntityRepository(db)
        self.device_repo = DeviceRepository(db)
        self.audit_service = AuditService(db)

    def execute_entity_command(
        self,
        *,
        entity_id: str,
        command: str,
        params: dict,
        actor_id: str | None,
        actor_type: str = "user",
    ) -> dict:
        entity = self.entity_repo.get_by_id(entity_id)
        if entity is None:
            raise ValueError("Entity not found")
        if not entity.writable:
            raise PermissionError("Entity is not writable")

        device = self.device_repo.get_by_id(entity.device_id)
        if device is None:
            raise ValueError("Device not found")

        settings = get_settings()
        topic = f"{settings.mqtt_topic_prefix}/device/{device.id}/cmd"
        payload = {
            "cmd_id": f"cmd_{uuid4().hex[:16]}",
            "ts": datetime.now(UTC).isoformat(),
            "type": "entity.command",
            "target_entity_id": entity.id,
            "name": command,
            "params": params,
        }

        published = publish_json(topic, payload)
        if not published:
            raise RuntimeError("MQTT publish failed or MQTT is not enabled")

        self.audit_service.record_event(
            site_id=entity.site_id,
            actor_type=actor_type,
            actor_id=actor_id,
            action="entity.command_requested",
            target_type="entity",
            target_id=entity.id,
            severity="info",
            metadata_json=json.dumps({"command": command, "params": params, "topic": topic}),
        )

        return {
            "status": "queued",
            "topic": topic,
            "payload": payload,
        }
