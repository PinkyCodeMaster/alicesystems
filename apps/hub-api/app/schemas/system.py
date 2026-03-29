from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RoomTemplateItem(BaseModel):
    name: str = Field(min_length=2, max_length=255)


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str


class RootResponse(BaseModel):
    service: str
    version: str
    site_id: str
    site_name: str
    setup_completed: bool
    requires_onboarding: bool


class HubSetupStatusResponse(BaseModel):
    setup_completed: bool
    requires_onboarding: bool
    site_id: str
    site_name: str
    timezone: str
    owner_count: int
    completed_at: datetime | None
    source: str


class HubSetupRequest(BaseModel):
    site_name: str = Field(min_length=2, max_length=255)
    timezone: str = Field(min_length=3, max_length=64)
    owner_email: EmailStr
    owner_display_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=8, max_length=255)
    room_names: list[str] | None = None


class HubSetupResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    display_name: str
    setup_completed: bool
    site_id: str
    site_name: str
    timezone: str
    rooms: list[RoomTemplateItem]


class AutoLightSettingsResponse(BaseModel):
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
    updated_at: datetime | None


class AutoLightSettingsUpdateRequest(BaseModel):
    enabled: bool
    sensor_entity_id: str | None = None
    target_entity_id: str | None = None
    motion_entity_id: str | None = None
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
