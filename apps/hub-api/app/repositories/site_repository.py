from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.site import Site


class SiteRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_first(self) -> Site | None:
        return self.db.scalar(select(Site).limit(1))

    def create(self, site: Site) -> Site:
        self.db.add(site)
        self.db.commit()
        self.db.refresh(site)
        return site

    def update(self, site: Site) -> Site:
        self.db.add(site)
        self.db.commit()
        self.db.refresh(site)
        return site
