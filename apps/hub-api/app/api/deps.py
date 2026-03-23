from collections.abc import Generator

from app.core.config import Settings, get_settings
from app.core.db import get_db_session
from app.domain.user import User
from app.services.auth_service import AuthService
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session


def get_db() -> Generator[Session, None, None]:
    yield from get_db_session()


def get_app_settings() -> Settings:
    return get_settings()


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    token = authorization.removeprefix("Bearer ").strip()
    user = AuthService(db).get_user_from_token(token)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return user
