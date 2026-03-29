from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Alice Assistant Runtime"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    cors_allow_origins: str = "*"
    assistant_mode: str = "deterministic"
    assistant_allow_fallback: bool = True
    session_store_file: str = "./data/assistant.db"
    session_history_window: int = 8
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str | None = None
    ollama_timeout_seconds: float = 20.0
    home_os_base_url: str = "http://127.0.0.1:8000/api/v1"
    home_os_timeout_seconds: float = 10.0
    home_os_service_id: str = "assistant-runtime"
    home_os_service_secret: str | None = None
    home_os_env_fallback_file: str = Field(default="../hub-api/.env")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def home_os_env_fallback_path(self) -> Path:
        return Path(self.home_os_env_fallback_file).resolve()

    @property
    def session_store_path(self) -> Path:
        return Path(self.session_store_file).resolve()

    @property
    def cors_allow_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]


def load_home_os_service_credentials(settings: Settings) -> tuple[str, str | None]:
    path = settings.home_os_env_fallback_path
    values: dict[str, str] = {}
    if path.exists():
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()

    return (
        settings.home_os_service_id or values.get("ASSISTANT_SERVICE_ID") or "assistant-runtime",
        settings.home_os_service_secret or values.get("ASSISTANT_SERVICE_SECRET"),
    )
