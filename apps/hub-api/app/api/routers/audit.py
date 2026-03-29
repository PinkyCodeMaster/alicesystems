from app.api.deps import get_current_actor, get_db
from app.schemas.audit import AuditEventListItem, AuditEventListResponse
from app.services.audit_service import AuditService
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("", response_model=AuditEventListResponse)
def list_audit_events(
    limit: int = 50,
    db: Session = Depends(get_db),
    _current_actor=Depends(get_current_actor),
) -> AuditEventListResponse:
    service = AuditService(db)
    items = [AuditEventListItem.model_validate(event) for event in service.list_recent(limit=limit)]
    return AuditEventListResponse(items=items)
