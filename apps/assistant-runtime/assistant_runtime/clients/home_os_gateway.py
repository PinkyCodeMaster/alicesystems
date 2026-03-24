from __future__ import annotations

import asyncio
from typing import Any

import httpx

from assistant_runtime.core.config import Settings, load_fallback_home_os_credentials
from assistant_runtime.models import AuditEvent, AutoLightSettings, Device, Entity, EntityState


class HomeOsGateway:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._token: str | None = None
        self._lock = asyncio.Lock()

    async def list_devices(self) -> list[Device]:
        data = await self._get("/devices")
        return [
            Device(
                id=item["id"],
                name=item["name"],
                device_type=item["device_type"],
                status=item["status"],
                fw_version=item.get("fw_version"),
            )
            for item in data["items"]
        ]

    async def list_entities(self) -> list[Entity]:
        data = await self._get("/entities")
        return [
            Entity(
                id=item["id"],
                device_id=item["device_id"],
                capability_id=item["capability_id"],
                kind=item["kind"],
                name=item["name"],
                writable=item["writable"],
            )
            for item in data["items"]
        ]

    async def list_entity_states(self) -> list[EntityState]:
        data = await self._get("/entities/states")
        return [
            EntityState(
                entity_id=item["entity_id"],
                value=item["value"],
                source=item["source"],
                updated_at=item["updated_at"],
                version=item["version"],
            )
            for item in data["items"]
        ]

    async def get_stack_health(self) -> dict[str, Any]:
        return await self._get("/system/stack-health")

    async def get_auto_light_settings(self) -> AutoLightSettings:
        data = await self._get("/system/auto-light")
        return self._to_auto_light_settings(data)

    async def update_auto_light_enabled(self, *, enabled: bool) -> AutoLightSettings:
        current = await self.get_auto_light_settings()
        data = await self._request(
            "PUT",
            "/system/auto-light",
            json={
                "enabled": enabled,
                "sensor_entity_id": current.sensor_entity_id,
                "target_entity_id": current.target_entity_id,
                "mode": current.mode,
                "on_lux": current.on_lux,
                "off_lux": current.off_lux,
                "on_raw": current.on_raw,
                "off_raw": current.off_raw,
            },
        )
        return self._to_auto_light_settings(data)

    async def list_audit_events(self, *, limit: int = 5) -> list[AuditEvent]:
        data = await self._get(f"/audit-events?limit={limit}")
        return [
            AuditEvent(
                id=item["id"],
                actor_type=item["actor_type"],
                actor_id=item.get("actor_id"),
                action=item["action"],
                target_type=item["target_type"],
                target_id=item.get("target_id"),
                severity=item["severity"],
                metadata_json=item["metadata_json"],
                created_at=item["created_at"],
            )
            for item in data["items"]
        ]

    async def execute_entity_command(self, *, entity_id: str, command: str, params: dict) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/entities/{entity_id}/commands",
            json={"command": command, "params": params},
        )

    async def _get(self, path: str) -> dict[str, Any]:
        return await self._request("GET", path)

    async def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        token = await self._get_token()
        headers = kwargs.pop("headers", {})
        headers["Accept"] = "application/json"
        headers["Authorization"] = f"Bearer {token}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.request(
                method,
                f"{self.settings.home_os_base_url}{path}",
                headers=headers,
                **kwargs,
            )

        if response.status_code == 401:
            self._token = None
            token = await self._get_token(force_refresh=True)
            headers["Authorization"] = f"Bearer {token}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.request(
                    method,
                    f"{self.settings.home_os_base_url}{path}",
                    headers=headers,
                    **kwargs,
                )

        response.raise_for_status()
        return response.json()

    async def _get_token(self, *, force_refresh: bool = False) -> str:
        async with self._lock:
            if self._token is not None and not force_refresh:
                return self._token

            email, password = load_fallback_home_os_credentials(self.settings)
            if not email or not password:
                raise RuntimeError(
                    "Assistant runtime is missing Home OS credentials. "
                    "Set HOME_OS_EMAIL/HOME_OS_PASSWORD or keep DEFAULT_ADMIN_* in apps/hub-api/.env."
                )

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.settings.home_os_base_url}/auth/login",
                    json={"email": email, "password": password},
                    headers={"Accept": "application/json"},
                )
            response.raise_for_status()
            self._token = response.json()["access_token"]
            return self._token

    def _to_auto_light_settings(self, data: dict[str, Any]) -> AutoLightSettings:
        return AutoLightSettings(
            enabled=data["enabled"],
            sensor_entity_id=data.get("sensor_entity_id"),
            target_entity_id=data.get("target_entity_id"),
            mode=data["mode"],
            on_lux=data["on_lux"],
            off_lux=data["off_lux"],
            on_raw=data["on_raw"],
            off_raw=data["off_raw"],
            source=data["source"],
            updated_at=data.get("updated_at"),
        )
