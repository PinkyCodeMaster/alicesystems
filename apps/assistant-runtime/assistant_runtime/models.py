from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Device:
    id: str
    name: str
    device_type: str
    status: str
    fw_version: str | None


@dataclass
class Entity:
    id: str
    device_id: str
    capability_id: str
    kind: str
    name: str
    writable: int


@dataclass
class EntityState:
    entity_id: str
    value: dict
    source: str
    updated_at: str
    version: int


@dataclass
class AutoLightSettings:
    enabled: bool
    sensor_entity_id: str | None
    target_entity_id: str | None
    motion_entity_id: str | None
    mode: str
    on_lux: float
    off_lux: float
    on_raw: float
    off_raw: float
    block_on_during_daytime: bool
    daytime_start_hour: int
    daytime_end_hour: int
    allow_daytime_turn_on_when_very_dark: bool
    daytime_on_lux: float
    daytime_on_raw: float
    require_motion_for_turn_on: bool
    motion_hold_seconds: int
    source: str
    updated_at: str | None


@dataclass
class AuditEvent:
    id: str
    actor_type: str
    actor_id: str | None
    action: str
    target_type: str
    target_id: str | None
    severity: str
    metadata_json: str
    created_at: str


@dataclass
class DeviceDetailEntity:
    id: str
    capability_id: str
    kind: str
    name: str
    writable: int
    state: dict | None
    state_source: str | None
    state_updated_at: str | None
    state_version: int | None


@dataclass
class DeviceDetail:
    device: Device
    entities: list[DeviceDetailEntity]
    audit_events: list[AuditEvent]


@dataclass
class SessionMessage:
    id: int
    session_id: str
    role: str
    content: str
    created_at: str
    mode: str | None
    success: bool | None
    metadata: dict[str, Any]
