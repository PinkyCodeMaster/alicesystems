from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.domain.system_setting import SystemSetting
from app.repositories.system_setting_repository import SystemSettingRepository
from app.services.site_service import SiteService

AUTO_LIGHT_SETTINGS_KEY = "system:auto-light"


@dataclass
class AutoLightSettings:
    enabled: bool
    sensor_entity_id: str | None
    target_entity_id: str | None
    mode: str
    on_lux: float
    off_lux: float
    on_raw: float
    off_raw: float
    block_on_during_daytime: bool
    daytime_start_hour: int
    daytime_end_hour: int
    source: str
    updated_at: datetime | None = None


class AutoLightSettingsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = SystemSettingRepository(db)
        self.site_service = SiteService(db)

    def get(self) -> AutoLightSettings:
        setting = self.repo.get_by_key(AUTO_LIGHT_SETTINGS_KEY)
        if setting is None:
            return self._from_env()

        payload = json.loads(setting.value_json)
        settings = get_settings()
        return AutoLightSettings(
            enabled=bool(payload.get("enabled", settings.auto_light_enabled)),
            sensor_entity_id=payload.get("sensor_entity_id"),
            target_entity_id=payload.get("target_entity_id"),
            mode=str(payload.get("mode", settings.auto_light_mode)),
            on_lux=float(payload.get("on_lux", settings.auto_light_on_lux)),
            off_lux=float(payload.get("off_lux", settings.auto_light_off_lux)),
            on_raw=float(payload.get("on_raw", settings.auto_light_on_raw)),
            off_raw=float(payload.get("off_raw", settings.auto_light_off_raw)),
            block_on_during_daytime=bool(
                payload.get(
                    "block_on_during_daytime",
                    settings.auto_light_block_on_during_daytime,
                )
            ),
            daytime_start_hour=int(
                payload.get("daytime_start_hour", settings.auto_light_daytime_start_hour)
            ),
            daytime_end_hour=int(
                payload.get("daytime_end_hour", settings.auto_light_daytime_end_hour)
            ),
            source="db",
            updated_at=setting.updated_at,
        )

    def save(
        self,
        *,
        enabled: bool,
        sensor_entity_id: str | None,
        target_entity_id: str | None,
        mode: str,
        on_lux: float,
        off_lux: float,
        on_raw: float,
        off_raw: float,
        block_on_during_daytime: bool,
        daytime_start_hour: int,
        daytime_end_hour: int,
    ) -> AutoLightSettings:
        now = datetime.now(UTC).replace(tzinfo=None)
        site = self.site_service.get_or_create_default_site()
        payload = {
            "enabled": enabled,
            "sensor_entity_id": sensor_entity_id,
            "target_entity_id": target_entity_id,
            "mode": mode,
            "on_lux": on_lux,
            "off_lux": off_lux,
            "on_raw": on_raw,
            "off_raw": off_raw,
            "block_on_during_daytime": block_on_during_daytime,
            "daytime_start_hour": daytime_start_hour,
            "daytime_end_hour": daytime_end_hour,
        }
        setting = self.repo.get_by_key(AUTO_LIGHT_SETTINGS_KEY)
        if setting is None:
            setting = SystemSetting(
                key=AUTO_LIGHT_SETTINGS_KEY,
                site_id=site.id,
                value_json=json.dumps(payload, sort_keys=True),
                updated_at=now,
            )
        else:
            setting.value_json = json.dumps(payload, sort_keys=True)
            setting.updated_at = now

        saved = self.repo.save(setting)
        return AutoLightSettings(**payload, source="db", updated_at=saved.updated_at)

    def _from_env(self) -> AutoLightSettings:
        settings = get_settings()
        return AutoLightSettings(
            enabled=settings.auto_light_enabled,
            sensor_entity_id=settings.auto_light_sensor_entity_id,
            target_entity_id=settings.auto_light_target_entity_id,
            mode=settings.auto_light_mode,
            on_lux=settings.auto_light_on_lux,
            off_lux=settings.auto_light_off_lux,
            on_raw=settings.auto_light_on_raw,
            off_raw=settings.auto_light_off_raw,
            block_on_during_daytime=settings.auto_light_block_on_during_daytime,
            daytime_start_hour=settings.auto_light_daytime_start_hour,
            daytime_end_hour=settings.auto_light_daytime_end_hour,
            source="env",
            updated_at=None,
        )
