from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entity_state import EntityState


class EntityStateRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, entity_id: str) -> EntityState | None:
        stmt = select(EntityState).where(EntityState.entity_id == entity_id)
        return self.db.scalar(stmt)

    def list_by_entity_ids(self, entity_ids: list[str]) -> list[EntityState]:
        if not entity_ids:
            return []
        stmt = select(EntityState).where(EntityState.entity_id.in_(entity_ids))
        return list(self.db.scalars(stmt).all())

    def save(self, state: EntityState) -> EntityState:
        self.db.add(state)
        self.db.commit()
        self.db.refresh(state)
        return state
