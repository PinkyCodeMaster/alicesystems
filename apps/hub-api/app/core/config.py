from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_settings_override = None


class Settings(BaseSettings):
    app_name: str = "Alice Home OS API"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    timezone: str = "Europe/London"
    database_url: str = Field(
        default="sqlite:///./data/alice.db",
        description="SQLAlchemy database URL for the Home OS canonical store.",
    )
    jwt_secret: str = Field(default="dev-only-secret-change-me-at-least-32-bytes")
    jwt_algorithm: str = "HS256"
    access_token_expiry_minutes: int = 720
    mqtt_enabled: bool = False
    mqtt_host: str = "127.0.0.1"
    mqtt_port: int = 1883
    mqtt_username: str | None = None
    mqtt_password: str | None = None
    mqtt_client_id: str = "alice-hub-api"
    mqtt_topic_prefix: str = "alice/v1"
    cors_allow_origins: str = "http://127.0.0.1:3000,http://localhost:3000"
    log_level: str = "INFO"
    log_dir: str = Field(default=str(Path(".") / "logs"))
    log_filename: str = "hub-api.log"
    log_json_filename: str = "hub-api.jsonl"
    log_http_request_bodies: bool = False
    log_http_request_body_max_bytes: int = 4096
    log_http_include_docs_requests: bool = False
    auto_light_enabled: bool = False
    auto_light_sensor_entity_id: str | None = None
    auto_light_target_entity_id: str | None = None
    auto_light_mode: str = "lux_low_turn_on"
    auto_light_on_lux: float = 120.0
    auto_light_off_lux: float = 220.0
    auto_light_on_raw: float = 3000.0
    auto_light_off_raw: float = 2600.0
    auto_light_block_on_during_daytime: bool = True
    auto_light_daytime_start_hour: int = 7
    auto_light_daytime_end_hour: int = 18
    auto_light_allow_daytime_turn_on_when_very_dark: bool = True
    auto_light_daytime_on_lux: float = 35.0
    auto_light_daytime_on_raw: float = 3600.0
    auto_light_motion_entity_id: str | None = None
    auto_light_require_motion_for_turn_on: bool = False
    auto_light_motion_hold_seconds: int = 900
    auto_light_actor_id: str = "system:auto-light"
    device_offline_timeout_seconds: int = 45
    default_admin_email: str = "scottjones@wolfpackdefence.co.uk"
    default_admin_password: str = "Alltheballs!2"
    default_admin_display_name: str = "Scott Jones"
    enable_docs: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_allow_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]


@lru_cache
def _get_default_settings() -> Settings:
    return Settings()


def get_settings() -> Settings:
    if _settings_override is not None:
        return _settings_override
    return _get_default_settings()


def set_settings_override(settings: Settings | None) -> None:
    global _settings_override
    _settings_override = settings
    _get_default_settings.cache_clear()
