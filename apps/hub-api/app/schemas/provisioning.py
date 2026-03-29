from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DeviceBootstrapRecordItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    model: str
    device_type: str
    hardware_revision: str | None
    default_device_id: str | None
    status: str
    claimed_device_id: str | None
    metadata_json: str
    created_at: datetime
    updated_at: datetime
    claimed_at: datetime | None


class DeviceBootstrapRecordCreateRequest(BaseModel):
    bootstrap_id: str = Field(min_length=3, max_length=64)
    model: str = Field(min_length=1, max_length=128)
    device_type: str = Field(min_length=1, max_length=64)
    setup_code: str = Field(min_length=4, max_length=32)
    hardware_revision: str | None = Field(default=None, max_length=64)
    default_device_id: str | None = Field(default=None, max_length=64)
    metadata: dict = Field(default_factory=dict)


class ProvisioningSessionCreateRequest(BaseModel):
    bootstrap_id: str = Field(min_length=3, max_length=64)
    setup_code: str = Field(min_length=4, max_length=32)
    room_id: str | None = Field(default=None, max_length=64)
    requested_device_name: str | None = Field(default=None, max_length=255)


class ProvisioningSessionResponse(BaseModel):
    session_id: str
    bootstrap_id: str
    status: str
    claim_token: str
    expires_at: datetime
    requested_device_name: str | None
    room_id: str | None


class ProvisioningSessionStatusResponse(BaseModel):
    session_id: str
    bootstrap_id: str
    status: str
    expires_at: datetime
    requested_device_name: str | None
    room_id: str | None
    claimed_device_id: str | None
    completed_at: datetime | None


class ProvisioningClaimCompleteRequest(BaseModel):
    bootstrap_id: str = Field(min_length=3, max_length=64)
    claim_token: str = Field(min_length=12, max_length=255)
    fw_version: str | None = Field(default=None, max_length=64)
    protocol: str = Field(default="wifi-mqtt", max_length=64)
    mqtt_client_id: str | None = Field(default=None, max_length=128)


class ProvisioningRuntimeConfigResponse(BaseModel):
    session_id: str
    bootstrap_id: str
    device_id: str
    site_id: str
    room_id: str | None
    device_name: str
    model: str
    device_type: str
    protocol: str
    provisioning_status: str
    mqtt_host: str
    mqtt_port: int
    mqtt_topic_prefix: str
    mqtt_client_id: str
    mqtt_username: str
    mqtt_password: str

