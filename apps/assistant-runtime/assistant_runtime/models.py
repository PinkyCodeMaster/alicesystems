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
class SessionMessage:
    id: int
    session_id: str
    role: str
    content: str
    created_at: str
    mode: str | None
    success: bool | None
    metadata: dict[str, Any]
