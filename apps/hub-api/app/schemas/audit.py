from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditEventListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    site_id: str
    actor_type: str
    actor_id: str | None
    action: str
    target_type: str
    target_id: str | None
    severity: str
    metadata_json: str
    created_at: datetime


class AuditEventListResponse(BaseModel):
    items: list[AuditEventListItem]
