from datetime import UTC, datetime
import json
import logging
from uuid import uuid4

from app.core.events import event_bus
from sqlalchemy.orm import Session

from app.domain.audit_event import AuditEvent
from app.repositories.audit_event_repository import AuditEventRepository

logger = logging.getLogger("alice.audit")


class AuditService:
    def __init__(self, db: Session) -> None:
        self.repo = AuditEventRepository(db)

    def record_event(
        self,
        *,
        site_id: str,
        actor_type: str,
        actor_id: str | None,
        action: str,
        target_type: str,
        target_id: str | None,
        severity: str = "info",
        metadata_json: str = "{}",
    ) -> AuditEvent:
        event_payload = {
            "site_id": site_id,
            "actor_type": actor_type,
            "actor_id": actor_id,
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "severity": severity,
            "metadata": json.loads(metadata_json) if metadata_json else {},
        }
        event = AuditEvent(
            id=f"audit_{uuid4().hex[:16]}",
            site_id=site_id,
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            severity=severity,
            metadata_json=metadata_json,
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        logger.info(
            "Audit event recorded",
            extra={"event": event_payload},
        )
        saved = self.repo.create(event)
        event_bus.publish(
            {
                "type": "audit_event",
                "action": saved.action,
                "target_id": saved.target_id,
                "actor_id": saved.actor_id,
                "severity": saved.severity,
                "created_at": saved.created_at.isoformat(),
                "metadata": event_payload["metadata"],
            }
        )
        return saved

    def list_recent(self, limit: int = 50) -> list[AuditEvent]:
        return self.repo.list_recent(limit=limit)

    def list_recent_by_action(self, *, action: str, limit: int = 50) -> list[AuditEvent]:
        return self.repo.list_recent_by_action(action=action, limit=limit)

    def list_recent_for_target(self, *, target_id: str, limit: int = 50) -> list[AuditEvent]:
        return self.repo.list_recent_for_target(target_id=target_id, limit=limit)
