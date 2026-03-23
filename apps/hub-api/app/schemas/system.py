from datetime import datetime

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str


class RootResponse(BaseModel):
    service: str
    version: str
    site_id: str
    site_name: str


class AutoLightSettingsResponse(BaseModel):
    enabled: bool
    sensor_entity_id: str | None
    target_entity_id: str | None
    mode: str
    on_lux: float
    off_lux: float
    on_raw: float
    off_raw: float
    source: str
    updated_at: datetime | None


class AutoLightSettingsUpdateRequest(BaseModel):
    enabled: bool
    sensor_entity_id: str | None = None
    target_entity_id: str | None = None
    mode: str
    on_lux: float
    off_lux: float
    on_raw: float
    off_raw: float


class StackHealthBrokerStatus(BaseModel):
    enabled: bool
    host: str
    port: int
    started: bool
    connected: bool


class StackHealthDevicesStatus(BaseModel):
    total: int
    online: int
    offline: int
    timeout_seconds: int


class StackHealthCommandEvent(BaseModel):
    action: str
    target_id: str | None
    actor_id: str | None
    created_at: datetime
    metadata: dict


class StackHealthResponse(BaseModel):
    api_status: str
    api_service: str
    environment: str
    broker: StackHealthBrokerStatus
    devices: StackHealthDevicesStatus
    latest_command_request: StackHealthCommandEvent | None
    latest_command_ack: StackHealthCommandEvent | None
