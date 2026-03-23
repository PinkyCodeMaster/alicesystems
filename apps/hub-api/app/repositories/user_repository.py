from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.user import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return self.db.scalar(stmt)

    def get_by_id(self, user_id: str) -> User | None:
        stmt = select(User).where(User.id == user_id)
        return self.db.scalar(stmt)

    def list_admins(self, *, site_id: str | None = None) -> list[User]:
        stmt = select(User).where(User.role == "admin")
        if site_id is not None:
            stmt = stmt.where(User.site_id == site_id)
        return list(self.db.scalars(stmt).all())

    def update(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
