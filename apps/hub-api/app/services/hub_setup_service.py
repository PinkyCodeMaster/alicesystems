from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token
from app.domain.system_setting import SystemSetting
from app.domain.user import User
from app.repositories.system_setting_repository import SystemSettingRepository
from app.services.audit_service import AuditService
from app.services.room_service import RoomService
from app.services.site_service import SiteService
from app.services.user_service import UserService

HUB_SETUP_KEY = "system:hub-setup"
DEFAULT_ROOM_NAMES = [
    "Living Room",
    "Kitchen",
    "Dining Room",
    "Downstairs Bathroom",
    "Upstairs Bathroom",
    "Master Bedroom",
    "Kids Room",
]


@dataclass
class HubSetupStatus:
    setup_completed: bool
    requires_onboarding: bool
    site_id: str
    site_name: str
    timezone: str
    owner_count: int
    completed_at: datetime | None = None
    source: str = "derived"


@dataclass
class HubSetupResult:
    access_token: str
    token_type: str
    user_id: str
    display_name: str
    setup_completed: bool
    site_id: str
    site_name: str
    timezone: str
    rooms: list[dict[str, str]]


class HubSetupService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = SystemSettingRepository(db)
        self.site_service = SiteService(db)
        self.user_service = UserService(db)
        self.audit_service = AuditService(db)
        self.room_service = RoomService(db)

    def get_status(self) -> HubSetupStatus:
        site = self.site_service.get_or_create_default_site()
        owner_count = self.repo_count_users()
        setting = self.repo.get_by_key(HUB_SETUP_KEY)
        completed_at = setting.updated_at if setting is not None else None
        source = "db" if setting is not None else "derived"
        completed = owner_count > 0
        return HubSetupStatus(
            setup_completed=completed,
            requires_onboarding=not completed,
            site_id=site.id,
            site_name=site.name,
            timezone=site.timezone,
            owner_count=owner_count,
            completed_at=completed_at,
            source=source,
        )

    def complete_setup(
        self,
        *,
        site_name: str,
        timezone: str,
        owner_email: str,
        owner_display_name: str,
        password: str,
        room_names: list[str] | None = None,
    ) -> HubSetupResult:
        if self.user_service.has_any_users():
            raise ValueError("Hub setup has already been completed.")

        site = self.site_service.update_site(name=site_name.strip(), timezone=timezone.strip())
        owner = self.user_service.create_initial_owner(
            site_id=site.id,
            email=owner_email,
            display_name=owner_display_name,
            password=password,
        )
        room_items = self._create_initial_rooms(actor_id=owner.id, room_names=room_names)
        self._record_setup_complete(site_id=site.id, owner=owner)

        token = create_access_token(
            settings=get_settings(),
            user_id=owner.id,
            role=owner.role,
        )
        return HubSetupResult(
            access_token=token,
            token_type="bearer",
            user_id=owner.id,
            display_name=owner.display_name,
            setup_completed=True,
            site_id=site.id,
            site_name=site.name,
            timezone=site.timezone,
            rooms=room_items,
        )

    def repo_count_users(self) -> int:
        return self.user_service.repo.count_all()

    def _record_setup_complete(self, *, site_id: str, owner: User) -> None:
        now = datetime.now(UTC).replace(tzinfo=None)
        payload = {
            "owner_user_id": owner.id,
            "owner_email": owner.email,
            "completed_at": now.isoformat(),
        }
        setting = self.repo.get_by_key(HUB_SETUP_KEY)
        if setting is None:
            setting = SystemSetting(
                key=HUB_SETUP_KEY,
                site_id=site_id,
                value_json=json.dumps(payload, sort_keys=True),
                updated_at=now,
            )
        else:
            setting.site_id = site_id
            setting.value_json = json.dumps(payload, sort_keys=True)
            setting.updated_at = now
        self.repo.save(setting)

        self.audit_service.record_event(
            site_id=site_id,
            actor_type="user",
            actor_id=owner.id,
            action="system.hub_setup_completed",
            target_type="site",
            target_id=site_id,
            severity="info",
            metadata_json=json.dumps(
                {
                    "owner_email": owner.email,
                    "completed_at": now.isoformat(),
                },
                sort_keys=True,
            ),
        )

    def _create_initial_rooms(self, *, actor_id: str, room_names: list[str] | None) -> list[dict[str, str]]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for raw_name in room_names or DEFAULT_ROOM_NAMES:
            name = raw_name.strip()
            if len(name) < 2:
                continue
            slug = name.lower().replace(" ", "-")
            if slug in seen:
                continue
            seen.add(slug)
            cleaned.append(name)

        created_rooms: list[dict[str, str]] = []
        for name in cleaned:
            room, _ = self.room_service.create_room(name=name, actor_id=actor_id)
            created_rooms.append({"id": room.id, "name": room.name, "slug": room.slug})
        return created_rooms
