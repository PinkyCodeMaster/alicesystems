from datetime import UTC, datetime
import json

from sqlalchemy.orm import Session

from app.domain.entity_state import EntityState
from app.repositories.entity_repository import EntityRepository
from app.repositories.entity_state_repository import EntityStateRepository
from app.services.automation_service import AutomationService
from app.services.audit_service import AuditService


class EntityStateService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.entity_repo = EntityRepository(db)
        self.state_repo = EntityStateRepository(db)
        self.audit_service = AuditService(db)
        self.automation_service = AutomationService(db)

    def get_state(self, entity_id: str) -> EntityState | None:
        return self.state_repo.get(entity_id)

    def set_state(
        self,
        *,
        entity_id: str,
        value: dict,
        source: str,
        actor_id: str | None,
    ) -> EntityState:
        entity = self.entity_repo.get_by_id(entity_id)
        if entity is None:
            raise ValueError("Entity not found")

        existing = self.state_repo.get(entity_id)
        now = datetime.now(UTC).replace(tzinfo=None)
        payload = json.dumps(value, sort_keys=True)

        if existing is None:
            state = EntityState(
                entity_id=entity_id,
                value_json=payload,
                source=source,
                updated_at=now,
                version=1,
            )
        else:
            existing.value_json = payload
            existing.source = source
            existing.updated_at = now
            existing.version += 1
            state = existing

        saved = self.state_repo.save(state)
        self.audit_service.record_event(
            site_id=entity.site_id,
            actor_type="user" if actor_id else "system",
            actor_id=actor_id,
            action="entity_state.updated",
            target_type="entity",
            target_id=entity_id,
            severity="info",
            metadata_json=json.dumps({"source": source, "value": value}),
        )
        try:
            self.automation_service.process_entity_state_updated(
                entity_id=entity_id,
                value=value,
                source=source,
            )
        except (PermissionError, RuntimeError, ValueError) as exc:
            self.audit_service.record_event(
                site_id=entity.site_id,
                actor_type="system",
                actor_id="system:automation",
                action="automation.execution_failed",
                target_type="entity",
                target_id=entity_id,
                severity="warning",
                metadata_json=json.dumps({"source": source, "value": value, "error": str(exc)}),
            )
        return saved
