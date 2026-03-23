from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.domain.site import Site
from app.repositories.site_repository import SiteRepository


class SiteService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = SiteRepository(db)

    def get_or_create_default_site(self) -> Site:
        site = self.repo.get_first()
        if site is not None:
            return site

        settings = get_settings()
        now = datetime.now(UTC).replace(tzinfo=None)
        site = Site(
            id="site_home_01",
            name="Alice Home",
            timezone=settings.timezone,
            created_at=now,
            updated_at=now,
        )
        return self.repo.create(site)
