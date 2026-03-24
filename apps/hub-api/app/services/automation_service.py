from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.repositories.entity_repository import EntityRepository
from app.repositories.entity_state_repository import EntityStateRepository
from app.services.auto_light_settings_service import AutoLightSettingsService
from app.services.command_service import CommandService


class AutomationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.entity_repo = EntityRepository(db)
        self.state_repo = EntityStateRepository(db)
        self.command_service = CommandService(db)
        self.settings_service = AutoLightSettingsService(db)

    def process_entity_state_updated(self, *, entity_id: str, value: dict, source: str) -> None:
        runtime_settings = get_settings()
        settings = self.settings_service.get()
        if not settings.enabled:
            return
        if not settings.sensor_entity_id or not settings.target_entity_id:
            return
        if entity_id != settings.sensor_entity_id:
            return

        desired_on = self._desired_relay_state(
            value=value,
            mode=settings.mode,
            on_lux=settings.on_lux,
            off_lux=settings.off_lux,
            on_raw=settings.on_raw,
            off_raw=settings.off_raw,
        )
        if desired_on is None:
            return
        if desired_on and self._should_suppress_daytime_turn_on(
            block_on_during_daytime=settings.block_on_during_daytime,
            daytime_start_hour=settings.daytime_start_hour,
            daytime_end_hour=settings.daytime_end_hour,
        ):
            return

        target_entity = self.entity_repo.get_by_id(settings.target_entity_id)
        if target_entity is None or not target_entity.writable:
            return

        current_state = self.state_repo.get(target_entity.id)
        if current_state is not None:
            try:
                current_value = json.loads(current_state.value_json)
            except json.JSONDecodeError:
                current_value = {}
            if current_value.get("on") is desired_on:
                return

        self.command_service.execute_entity_command(
            entity_id=target_entity.id,
            command="switch.set",
            params={"on": desired_on},
            actor_id=runtime_settings.auto_light_actor_id,
            actor_type="system",
        )

    def _extract_lux(self, value: dict) -> float | None:
        lux = value.get("lux")
        if isinstance(lux, (int, float)):
            return float(lux)
        return None

    def _extract_raw(self, value: dict) -> float | None:
        raw = value.get("raw")
        if isinstance(raw, (int, float)):
            return float(raw)
        return None

    def _desired_relay_state(
        self,
        *,
        value: dict,
        mode: str,
        on_lux: float,
        off_lux: float,
        on_raw: float,
        off_raw: float,
    ) -> bool | None:
        if mode == "raw_high_turn_on":
            raw = self._extract_raw(value)
            if raw is None:
                return None
            if raw >= on_raw:
                return True
            if raw <= off_raw:
                return False
            return None

        lux = self._extract_lux(value)
        if lux is None:
            return None
        if lux <= on_lux:
            return True
        if lux >= off_lux:
            return False
        return None

    def _should_suppress_daytime_turn_on(
        self,
        *,
        block_on_during_daytime: bool,
        daytime_start_hour: int,
        daytime_end_hour: int,
    ) -> bool:
        if not block_on_during_daytime:
            return False

        current_hour = self._current_local_hour()
        if daytime_start_hour == daytime_end_hour:
            return False
        if daytime_start_hour < daytime_end_hour:
            return daytime_start_hour <= current_hour < daytime_end_hour
        return current_hour >= daytime_start_hour or current_hour < daytime_end_hour

    def _current_local_hour(self) -> int:
        settings = get_settings()
        return datetime.now(ZoneInfo(settings.timezone)).hour
