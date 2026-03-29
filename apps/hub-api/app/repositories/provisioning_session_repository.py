from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.provisioning_session import ProvisioningSession


class ProvisioningSessionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, session_id: str) -> ProvisioningSession | None:
        stmt = select(ProvisioningSession).where(ProvisioningSession.id == session_id)
        return self.db.scalar(stmt)

    def get_latest_for_bootstrap(self, bootstrap_id: str) -> ProvisioningSession | None:
        stmt = (
            select(ProvisioningSession)
            .where(ProvisioningSession.bootstrap_id == bootstrap_id)
            .order_by(ProvisioningSession.created_at.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def get_active_for_bootstrap(self, bootstrap_id: str, *, now: datetime) -> ProvisioningSession | None:
        stmt = (
            select(ProvisioningSession)
            .where(
                ProvisioningSession.bootstrap_id == bootstrap_id,
                ProvisioningSession.status == "pending",
                ProvisioningSession.expires_at > now,
            )
            .order_by(ProvisioningSession.created_at.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def save(self, session: ProvisioningSession) -> ProvisioningSession:
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session
