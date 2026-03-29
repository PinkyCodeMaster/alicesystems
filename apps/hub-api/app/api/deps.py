from dataclasses import dataclass
import hmac
from collections.abc import Generator

from app.core.config import Settings, get_settings
from app.core.db import get_db_session
from app.domain.user import User
from app.services.auth_service import AuthService
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class AuthenticatedActor:
    id: str
    role: str
    actor_type: str
    user: User | None = None


def get_db() -> Generator[Session, None, None]:
    yield from get_db_session()


def get_app_settings() -> Settings:
    return get_settings()


def get_current_actor(
    authorization: str | None = Header(default=None),
    alice_service_id: str | None = Header(default=None, alias="X-Alice-Service-Id"),
    alice_service_secret: str | None = Header(default=None, alias="X-Alice-Service-Secret"),
    db: Session = Depends(get_db),
) -> AuthenticatedActor:
    settings = get_settings()

    if alice_service_id is not None or alice_service_secret is not None:
        if not alice_service_id or not alice_service_secret:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing assistant service credentials",
            )

        if not (
            hmac.compare_digest(alice_service_id.strip(), settings.assistant_service_id)
            and hmac.compare_digest(alice_service_secret, settings.assistant_service_secret)
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid assistant service credentials",
            )

        return AuthenticatedActor(
            id=f"service:{settings.assistant_service_id}",
            role="service",
            actor_type="service",
            user=None,
        )

    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    token = authorization.removeprefix("Bearer ").strip()
    user = AuthService(db).get_user_from_token(token)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return AuthenticatedActor(
        id=user.id,
        role=user.role,
        actor_type="user",
        user=user,
    )


def get_current_user(current_actor: AuthenticatedActor = Depends(get_current_actor)) -> User:
    if current_actor.user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires an owner or admin session.",
        )
    return current_actor.user
