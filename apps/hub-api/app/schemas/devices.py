from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.audit import AuditEventListItem


class DeviceListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    site_id: str
    room_id: str | None
    name: str
    model: str
    device_type: str
    protocol: str
    status: str
    provisioning_status: str
    fw_version: str | None
    mqtt_client_id: str
    last_seen_at: datetime | None


class DeviceListResponse(BaseModel):
    items: list[DeviceListItem]


class DeviceDetailEntityItem(BaseModel):
    id: str
    capability_id: str
    kind: str
    name: str
    writable: int
    traits_json: str
    state: dict | None
    state_source: str | None
    state_updated_at: datetime | None
    state_version: int | None


class DeviceDetailResponse(BaseModel):
    device: DeviceListItem
    entities: list[DeviceDetailEntityItem]
    audit_events: list[AuditEventListItem]
