from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.domain.user import User
from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = UserRepository(db)

    def get_by_email(self, email: str) -> User | None:
        return self.repo.get_by_email(email=email)

    def get_by_id(self, user_id: str) -> User | None:
        return self.repo.get_by_id(user_id=user_id)

    def has_any_users(self) -> bool:
        return self.repo.count_all() > 0

    def ensure_default_admin(self, *, site_id: str) -> User:
        settings = get_settings()
        target_email = settings.default_admin_email.strip().lower()
        existing = self.repo.get_by_email(target_email)
        if existing is not None:
            return existing

        now = datetime.now(UTC).replace(tzinfo=None)
        user = User(
            id=f"usr_{uuid4().hex[:12]}",
            site_id=site_id,
            email=target_email,
            display_name=settings.default_admin_display_name,
            role="admin",
            password_hash=hash_password(settings.default_admin_password),
            is_active=1,
            created_at=now,
            updated_at=now,
        )
        return self.repo.create(user)

    def sync_default_admin(self, *, site_id: str) -> tuple[User, str]:
        settings = get_settings()
        target_email = settings.default_admin_email.strip().lower()
        now = datetime.now(UTC).replace(tzinfo=None)

        existing = self.repo.get_by_email(target_email)
        if existing is not None:
            existing.site_id = site_id
            existing.display_name = settings.default_admin_display_name
            existing.role = "admin"
            existing.password_hash = hash_password(settings.default_admin_password)
            existing.is_active = 1
            existing.updated_at = now
            return self.repo.update(existing), "updated_existing_email"

        admins = self.repo.list_admins(site_id=site_id)
        if len(admins) == 1:
            admin = admins[0]
            admin.email = target_email
            admin.display_name = settings.default_admin_display_name
            admin.role = "admin"
            admin.password_hash = hash_password(settings.default_admin_password)
            admin.is_active = 1
            admin.updated_at = now
            return self.repo.update(admin), "migrated_single_admin"

        if len(admins) == 0:
            return self.ensure_default_admin(site_id=site_id), "created"

        created = self.ensure_default_admin(site_id=site_id)
        return created, "created_additional_admin"

    def create_initial_owner(
        self,
        *,
        site_id: str,
        email: str,
        display_name: str,
        password: str,
    ) -> User:
        normalized_email = email.strip().lower()
        if self.has_any_users():
            raise ValueError("Hub setup has already been completed.")
        if self.repo.get_by_email(normalized_email) is not None:
            raise ValueError("A user with that email already exists.")

        now = datetime.now(UTC).replace(tzinfo=None)
        user = User(
            id=f"usr_{uuid4().hex[:12]}",
            site_id=site_id,
            email=normalized_email,
            display_name=display_name.strip(),
            role="admin",
            password_hash=hash_password(password),
            is_active=1,
            created_at=now,
            updated_at=now,
        )
        return self.repo.create(user)
