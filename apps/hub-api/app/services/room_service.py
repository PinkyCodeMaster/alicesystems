from datetime import UTC, datetime
import json
from uuid import uuid4

from sqlalchemy.orm import Session

from app.domain.room import Room
from app.repositories.room_repository import RoomRepository
from app.services.audit_service import AuditService
from app.services.site_service import SiteService


class RoomService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = RoomRepository(db)
        self.site_service = SiteService(db)
        self.audit_service = AuditService(db)

    def list_rooms(self):
        return self.repo.list_all()

    def create_room(self, *, name: str, actor_id: str) -> tuple[Room, bool]:
        site = self.site_service.get_or_create_default_site()
        slug = name.strip().lower().replace(" ", "-")
        existing = self.repo.find_by_slug(site_id=site.id, slug=slug)
        if existing is not None:
            return existing, False

        now = datetime.now(UTC).replace(tzinfo=None)
        room = Room(
            id=f"room_{uuid4().hex[:12]}",
            site_id=site.id,
            name=name.strip(),
            slug=slug,
            created_at=now,
            updated_at=now,
        )
        created = self.repo.create(room)
        self.audit_service.record_event(
            site_id=site.id,
            actor_type="user",
            actor_id=actor_id,
            action="room.created",
            target_type="room",
            target_id=created.id,
            severity="info",
            metadata_json=json.dumps({"name": created.name, "slug": created.slug}),
        )
        return created, True
