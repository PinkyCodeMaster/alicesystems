from sqlalchemy.orm import Session

from app.repositories.entity_repository import EntityRepository
from app.repositories.entity_state_repository import EntityStateRepository


class EntityService:
    def __init__(self, db: Session) -> None:
        self.repo = EntityRepository(db)
        self.state_repo = EntityStateRepository(db)

    def list_entities(self):
        return self.repo.list_all()

    def list_states(self):
        entities = self.repo.list_all()
        result = []
        for entity in entities:
            state = self.state_repo.get(entity.id)
            result.append((entity.id, state))
        return result
