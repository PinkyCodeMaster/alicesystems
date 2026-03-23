from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entity import Entity


class EntityRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_all(self) -> list[Entity]:
        return list(self.db.scalars(select(Entity).order_by(Entity.name)))

    def get_by_id(self, entity_id: str) -> Entity | None:
        stmt = select(Entity).where(Entity.id == entity_id)
        return self.db.scalar(stmt)

    def get_by_device_and_capability(self, device_id: str, capability_id: str) -> Entity | None:
        stmt = select(Entity).where(Entity.device_id == device_id, Entity.capability_id == capability_id)
        return self.db.scalar(stmt)

    def list_by_device(self, device_id: str) -> list[Entity]:
        stmt = select(Entity).where(Entity.device_id == device_id).order_by(Entity.name)
        return list(self.db.scalars(stmt).all())

    def save(self, entity: Entity) -> Entity:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity
