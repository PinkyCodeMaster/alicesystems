from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
