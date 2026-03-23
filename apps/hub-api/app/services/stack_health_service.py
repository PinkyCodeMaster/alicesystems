from __future__ import annotations

import json

from app.core.config import get_settings
from app.core.mqtt import get_mqtt_status
from app.repositories.device_repository import DeviceRepository
from app.schemas.system import (
    StackHealthBrokerStatus,
    StackHealthCommandEvent,
    StackHealthDevicesStatus,
    StackHealthResponse,
)
from app.services.audit_service import AuditService
from sqlalchemy.orm import Session


class StackHealthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.device_repo = DeviceRepository(db)
        self.audit_service = AuditService(db)

    def get(self) -> StackHealthResponse:
        devices = self.device_repo.list_all()
        online = sum(1 for device in devices if device.status == "online")
        offline = len(devices) - online
        mqtt_status = get_mqtt_status(self.settings)

        return StackHealthResponse(
            api_status="ok",
            api_service=self.settings.app_name,
            environment=self.settings.environment,
            broker=StackHealthBrokerStatus(**mqtt_status),
            devices=StackHealthDevicesStatus(
                total=len(devices),
                online=online,
                offline=offline,
                timeout_seconds=self.settings.device_offline_timeout_seconds,
            ),
            latest_command_request=self._latest_event("entity.command_requested"),
            latest_command_ack=self._latest_event("entity.command_acknowledged"),
        )

    def _latest_event(self, action: str) -> StackHealthCommandEvent | None:
        events = self.audit_service.list_recent_by_action(action=action, limit=1)
        if not events:
            return None

        event = events[0]
        return StackHealthCommandEvent(
            action=event.action,
            target_id=event.target_id,
            actor_id=event.actor_id,
            created_at=event.created_at,
            metadata=json.loads(event.metadata_json or "{}"),
        )
