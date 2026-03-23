from pydantic import BaseModel, ConfigDict


class RoomCreateRequest(BaseModel):
    name: str


class RoomListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    site_id: str
    name: str
    slug: str


class RoomListResponse(BaseModel):
    items: list[RoomListItem]
