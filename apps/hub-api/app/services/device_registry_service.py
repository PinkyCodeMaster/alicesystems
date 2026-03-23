from __future__ import annotations

from datetime import UTC, datetime
import json
import logging
import re
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.domain.device import Device
from app.domain.entity import Entity
from app.repositories.device_repository import DeviceRepository
from app.repositories.entity_repository import EntityRepository
from app.services.audit_service import AuditService
from app.services.site_service import SiteService

_CAPABILITY_PRESETS = {
    "alice.sensor.env.s1": [
        {
            "capability_id": "temperature",
            "kind": "sensor.temperature",
            "name": "Temperature",
            "slug": "temperature",
            "writable": 0,
            "traits": {"unit": "C"},
        },
        {
            "capability_id": "illuminance",
            "kind": "sensor.illuminance",
            "name": "Illuminance",
            "slug": "illuminance",
            "writable": 0,
            "traits": {"unit": "lux"},
        },
        {
            "capability_id": "motion",
            "kind": "sensor.motion",
            "name": "Motion",
            "slug": "motion",
            "writable": 0,
            "traits": {},
        },
    ],
    "alice.relay.r1": [
        {
            "capability_id": "relay",
            "kind": "switch.relay",
            "name": "Light",
            "slug": "light",
            "writable": 1,
            "traits": {},
        }
    ],
}

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _slugify(value: str) -> str:
    value = value.strip().lower()
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def _entity_id(device_id: str, capability_id: str) -> str:
    compact = re.sub(r"[^a-zA-Z0-9]+", "_", f"{device_id}_{capability_id}")
    return f"ent_{compact[:56]}"


class DeviceRegistryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.device_repo = DeviceRepository(db)
        self.entity_repo = EntityRepository(db)
        self.site_service = SiteService(db)
        self.audit_service = AuditService(db)

    def list_devices(self) -> list[Device]:
        devices = self.device_repo.list_all()
        for device in devices:
            self._apply_offline_timeout(device, emit_audit=True)
        return devices

    def get_device(self, device_id: str) -> Device | None:
        device = self.device_repo.get_by_id(device_id)
        if device is not None:
            self._apply_offline_timeout(device, emit_audit=True)
        return device

    def upsert_from_hello(self, *, device_id: str, payload: dict) -> Device:
        site = self.site_service.get_or_create_default_site()
        now = _now()
        device = self.device_repo.get_by_id(device_id)

        if device is None:
            device = Device(
                id=device_id,
                site_id=site.id,
                room_id=payload.get("room_id"),
                name=payload.get("name") or device_id,
                model=payload.get("model") or "prototype.unknown",
                device_type=payload.get("device_type") or "unknown",
                protocol=payload.get("protocol") or "wifi-mqtt",
                status="online",
                provisioning_status="mqtt_discovered",
                fw_version=payload.get("fw_version"),
                mqtt_client_id=payload.get("mqtt_client_id") or device_id,
                capability_descriptor_json=json.dumps(payload.get("capabilities", []), sort_keys=True),
                last_seen_at=now,
                created_at=now,
                updated_at=now,
            )
        else:
            device.room_id = payload.get("room_id", device.room_id)
            device.name = payload.get("name") or device.name
            device.model = payload.get("model") or device.model
            device.device_type = payload.get("device_type") or device.device_type
            device.protocol = payload.get("protocol") or device.protocol
            device.status = "online"
            device.provisioning_status = "mqtt_discovered"
            device.fw_version = payload.get("fw_version") or device.fw_version
            device.mqtt_client_id = payload.get("mqtt_client_id") or device.mqtt_client_id
            device.capability_descriptor_json = json.dumps(payload.get("capabilities", []), sort_keys=True)
            device.last_seen_at = now
            device.updated_at = now

        saved = self.device_repo.save(device)
        for capability in self._capabilities_for(payload, saved):
            self._upsert_entity(saved, capability)
        logger.info(
            "Device hello processed",
            extra={
                "event": {
                    "action": "device.hello_processed",
                    "device_id": saved.id,
                    "model": saved.model,
                    "device_type": saved.device_type,
                }
            },
        )

        self.audit_service.record_event(
            site_id=saved.site_id,
            actor_type="device",
            actor_id=saved.id,
            action="device.hello_received",
            target_type="device",
            target_id=saved.id,
            severity="info",
            metadata_json=json.dumps({"model": saved.model, "device_type": saved.device_type}),
        )
        return saved

    def update_availability(self, *, device_id: str, status: str) -> Device | None:
        device = self.device_repo.get_by_id(device_id)
        if device is None:
            return None

        device.status = status
        device.last_seen_at = _now()
        device.updated_at = device.last_seen_at
        saved = self.device_repo.save(device)
        logger.info(
            "Device availability updated",
            extra={
                "event": {
                    "action": "device.availability_updated",
                    "device_id": saved.id,
                    "status": status,
                }
            },
        )
        self.audit_service.record_event(
            site_id=saved.site_id,
            actor_type="device",
            actor_id=saved.id,
            action="device.availability_updated",
            target_type="device",
            target_id=saved.id,
            severity="info",
            metadata_json=json.dumps({"status": status}),
        )
        return saved

    def mark_seen(self, *, device_id: str, status: str = "online") -> Device | None:
        device = self.device_repo.get_by_id(device_id)
        if device is None:
            return None
        now = _now()
        device.status = status
        device.last_seen_at = now
        device.updated_at = now
        return self.device_repo.save(device)

    def _apply_offline_timeout(self, device: Device, *, emit_audit: bool) -> None:
        settings = get_settings()
        if device.last_seen_at is None:
            return
        cutoff = _now() - timedelta(seconds=settings.device_offline_timeout_seconds)
        if device.last_seen_at >= cutoff or device.status == "offline":
            return

        device.status = "offline"
        device.updated_at = _now()
        self.device_repo.save(device)
        logger.info(
            "Device marked offline after heartbeat timeout",
            extra={"event": {"action": "device.offline_timeout", "device_id": device.id, "status": "offline"}},
        )
        if emit_audit:
            self.audit_service.record_event(
                site_id=device.site_id,
                actor_type="system",
                actor_id="system:presence",
                action="device.offline_timeout",
                target_type="device",
                target_id=device.id,
                severity="warning",
                metadata_json=json.dumps({"timeout_seconds": settings.device_offline_timeout_seconds}),
            )

    def _capabilities_for(self, payload: dict, device: Device) -> list[dict]:
        declared = payload.get("capabilities")
        if isinstance(declared, list) and declared:
            return declared

        if device.model in _CAPABILITY_PRESETS:
            return _CAPABILITY_PRESETS[device.model]

        if device.device_type == "sensor_node":
            return _CAPABILITY_PRESETS["alice.sensor.env.s1"]
        if device.device_type == "relay_node":
            return _CAPABILITY_PRESETS["alice.relay.r1"]
        return []

    def _upsert_entity(self, device: Device, capability: dict) -> Entity:
        capability_id = capability.get("capability_id") or capability.get("id") or capability.get("kind")
        existing = self.entity_repo.get_by_device_and_capability(device.id, capability_id)
        now = _now()
        default_name = f"{device.name} {capability.get('name', capability_id)}".strip()
        default_slug = _slugify(f"{device.name}-{capability.get('slug', capability_id)}")

        if existing is None:
            entity = Entity(
                id=_entity_id(device.id, capability_id),
                site_id=device.site_id,
                room_id=device.room_id,
                device_id=device.id,
                capability_id=capability_id,
                kind=capability.get("kind", capability_id),
                name=capability.get("entity_name") or default_name,
                slug=capability.get("entity_slug") or default_slug,
                writable=int(capability.get("writable", 0)),
                traits_json=json.dumps(capability.get("traits", {}), sort_keys=True),
                created_at=now,
                updated_at=now,
            )
        else:
            existing.room_id = device.room_id
            existing.kind = capability.get("kind", existing.kind)
            existing.name = capability.get("entity_name") or existing.name
            existing.slug = capability.get("entity_slug") or existing.slug
            existing.writable = int(capability.get("writable", existing.writable))
            existing.traits_json = json.dumps(capability.get("traits", {}), sort_keys=True)
            existing.updated_at = now
            entity = existing

        return self.entity_repo.save(entity)
