from __future__ import annotations

from datetime import UTC, datetime
import json

import jwt
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, decode_access_token, verify_password
from app.domain.user import User
from app.services.audit_service import AuditService
from app.services.site_service import SiteService
from app.services.user_service import UserService


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.user_service = UserService(db)
        self.site_service = SiteService(db)
        self.audit_service = AuditService(db)

    def authenticate(self, *, email: str, password: str) -> tuple[str, User] | None:
        user = self.user_service.get_by_email(email.strip().lower())
        if user is None or not verify_password(password, user.password_hash) or not user.is_active:
            site = self.site_service.get_or_create_default_site()
            self.audit_service.record_event(
                site_id=site.id,
                actor_type="anonymous",
                actor_id=None,
                action="auth.login_failed",
                target_type="user",
                target_id=email.strip().lower(),
                severity="warning",
                metadata_json=json.dumps({"email": email.strip().lower()}),
            )
            return None

        token = create_access_token(settings=get_settings(), user_id=user.id, role=user.role)
        self.audit_service.record_event(
            site_id=user.site_id,
            actor_type="user",
            actor_id=user.id,
            action="auth.login_succeeded",
            target_type="user",
            target_id=user.id,
            severity="info",
            metadata_json=json.dumps({"login_at": datetime.now(UTC).isoformat()}),
        )
        return token, user

    def get_user_from_token(self, token: str) -> User | None:
        try:
            payload = decode_access_token(settings=get_settings(), token=token)
        except jwt.InvalidTokenError:
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None
        return self.user_service.get_by_id(user_id)
