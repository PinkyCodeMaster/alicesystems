from __future__ import annotations

from datetime import UTC, datetime
import json
import re

from sqlalchemy.orm import Session

from app.repositories.entity_repository import EntityRepository
from app.services.audit_service import AuditService
from app.services.device_registry_service import DeviceRegistryService
from app.services.entity_state_service import EntityStateService

_DEVICE_TOPIC_RE = re.compile(
    r"^(?P<prefix>.+)/device/(?P<device_id>[^/]+)/(?P<message_type>hello|availability|telemetry|state|ack)$"
)
_META_KEYS = {"msg_id", "ts", "schema", "device_id", "fw_version", "boot_id"}


class MqttIngestService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.device_registry = DeviceRegistryService(db)
        self.entity_repo = EntityRepository(db)
        self.entity_state_service = EntityStateService(db)
        self.audit_service = AuditService(db)

    def process_message(self, topic: str, payload_text: str) -> None:
        match = _DEVICE_TOPIC_RE.match(topic)
        if match is None:
            return

        device_id = match.group("device_id")
        message_type = match.group("message_type")
        payload = self._parse_payload(payload_text)

        if message_type == "hello":
            self._handle_hello(device_id=device_id, payload=payload)
        elif message_type == "availability":
            self._handle_availability(device_id=device_id, payload=payload)
        elif message_type == "ack":
            self._handle_ack(device_id=device_id, payload=payload)
        else:
            self._handle_state_like(device_id=device_id, payload=payload, source=f"mqtt.{message_type}")

    def _handle_hello(self, *, device_id: str, payload: dict) -> None:
        body = self._body(payload)
        self.device_registry.upsert_from_hello(device_id=device_id, payload=body)

    def _handle_availability(self, *, device_id: str, payload) -> None:
        if isinstance(payload, dict):
            status = str(self._body(payload).get("status", "online"))
        else:
            status = str(payload)
        self.device_registry.update_availability(device_id=device_id, status=status)

    def _handle_ack(self, *, device_id: str, payload: dict) -> None:
        body = self._body(payload)
        device = self.device_registry.mark_seen(device_id=device_id, status="online")
        if device is None:
            self._record_unmapped(device_id=device_id, source="mqtt.ack", reason="unknown_device")
            return

        target_entity_id = body.get("target_entity_id")
        status = str(body.get("status", "ack"))
        metadata = {
            "cmd_id": body.get("cmd_id"),
            "status": status,
            "command": body.get("name"),
            "params": body.get("params", {}),
            "state": body.get("state", {}),
        }
        self.audit_service.record_event(
            site_id=device.site_id,
            actor_type="device",
            actor_id=device_id,
            action="entity.command_acknowledged",
            target_type="entity" if target_entity_id else "device",
            target_id=target_entity_id or device_id,
            severity="info",
            metadata_json=json.dumps(metadata),
        )

    def _handle_state_like(self, *, device_id: str, payload: dict, source: str) -> None:
        body = self._body(payload)
        capability_id = body.get("capability_id") or body.get("capability") or body.get("kind")
        if not capability_id:
            self._record_unmapped(device_id=device_id, source=source, reason="missing_capability")
            return

        device = self.device_registry.get_device(device_id)
        if device is None:
            self._record_unmapped(device_id=device_id, source=source, reason="unknown_device")
            return

        entity = self.entity_repo.get_by_device_and_capability(device_id, capability_id)
        if entity is None:
            self._record_unmapped(device_id=device_id, source=source, reason="unknown_entity", capability_id=capability_id)
            return

        state_value = self._state_value(body)
        self.entity_state_service.set_state(
            entity_id=entity.id,
            value=state_value,
            source=source,
            actor_id=None,
        )
        device.status = "online"
        device.last_seen_at = datetime.now(UTC).replace(tzinfo=None)
        device.updated_at = device.last_seen_at
        self.device_registry.device_repo.save(device)

    def _record_unmapped(self, *, device_id: str, source: str, reason: str, capability_id: str | None = None) -> None:
        device = self.device_registry.get_device(device_id)
        site_id = device.site_id if device is not None else self.device_registry.site_service.get_or_create_default_site().id
        self.audit_service.record_event(
            site_id=site_id,
            actor_type="device",
            actor_id=device_id,
            action="mqtt.message_unmapped",
            target_type="device",
            target_id=device_id,
            severity="warning",
            metadata_json=json.dumps({"source": source, "reason": reason, "capability_id": capability_id}),
        )

    def _parse_payload(self, payload_text: str):
        try:
            return json.loads(payload_text)
        except json.JSONDecodeError:
            return payload_text.strip()

    def _body(self, payload):
        if isinstance(payload, dict) and isinstance(payload.get("body"), dict):
            return payload["body"]
        if isinstance(payload, dict):
            return payload
        return {"value": payload}

    def _state_value(self, body: dict) -> dict:
        if isinstance(body.get("value"), dict):
            return body["value"]

        return {
            key: value
            for key, value in body.items()
            if key not in _META_KEYS and key not in {"capability", "capability_id", "kind"}
        }
