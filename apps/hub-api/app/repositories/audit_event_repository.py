from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.audit_event import AuditEvent


class AuditEventRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, event: AuditEvent) -> AuditEvent:
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def list_recent(self, limit: int = 50) -> list[AuditEvent]:
        stmt = select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)
        return list(self.db.scalars(stmt))

    def list_recent_by_action(self, *, action: str, limit: int = 50) -> list[AuditEvent]:
        stmt = (
            select(AuditEvent)
            .where(AuditEvent.action == action)
            .order_by(AuditEvent.created_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt))
