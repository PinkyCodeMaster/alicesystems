from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EntityListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    site_id: str
    room_id: str | None
    device_id: str
    capability_id: str
    kind: str
    name: str
    slug: str
    writable: int
    traits_json: str


class EntityListResponse(BaseModel):
    items: list[EntityListItem]


class EntityStateListItem(BaseModel):
    entity_id: str
    value: dict
    source: str
    updated_at: datetime
    version: int


class EntityStateListResponse(BaseModel):
    items: list[EntityStateListItem]


class EntityStateUpdateRequest(BaseModel):
    value: dict
    source: str


class EntityStateResponse(BaseModel):
    entity_id: str
    value: dict
    source: str
    updated_at: datetime
    version: int


class EntityCommandRequest(BaseModel):
    command: str
    params: dict = {}


class EntityCommandResponse(BaseModel):
    status: str
    topic: str
    payload: dict
