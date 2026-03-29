from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.room import Room


class RoomRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_all(self) -> list[Room]:
        return list(self.db.scalars(select(Room).order_by(Room.name)))

    def get_by_id(self, room_id: str) -> Room | None:
        stmt = select(Room).where(Room.id == room_id)
        return self.db.scalar(stmt)

    def create(self, room: Room) -> Room:
        self.db.add(room)
        self.db.commit()
        self.db.refresh(room)
        return room

    def find_by_slug(self, site_id: str, slug: str) -> Room | None:
        stmt = select(Room).where(Room.site_id == site_id, Room.slug == slug)
        return self.db.scalar(stmt)
