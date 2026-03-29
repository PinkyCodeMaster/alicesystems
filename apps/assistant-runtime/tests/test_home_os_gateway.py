from __future__ import annotations

import asyncio

import httpx

from assistant_runtime.clients.home_os_gateway import HomeOsGateway
from assistant_runtime.core.config import Settings


def test_gateway_reuses_login_token_across_requests() -> None:
    requests: list[tuple[str, str, str | None, str | None]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(
            (
                request.method,
                request.url.path,
                request.headers.get("x-alice-service-id"),
                request.headers.get("x-alice-service-secret"),
            )
        )
        if request.url.path == "/api/v1/devices":
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": "device_1",
                            "name": "Hallway Lamp",
                            "device_type": "relay",
                            "status": "online",
                            "fw_version": "1.0.0",
                        }
                    ]
                },
            )
        raise AssertionError(f"Unexpected request path: {request.url.path}")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    gateway = HomeOsGateway(
        Settings(
            home_os_base_url="http://alice.local/api/v1",
            home_os_service_id="assistant-runtime",
            home_os_service_secret="service-secret",
        ),
        client=client,
    )

    async def run() -> None:
        devices = await gateway.list_devices()
        assert devices[0].name == "Hallway Lamp"
        await gateway.list_devices()
        await client.aclose()

    asyncio.run(run())

    device_requests = [entry for entry in requests if entry[1] == "/api/v1/devices"]

    assert len(device_requests) == 2
    assert all(service_id == "assistant-runtime" for _, _, service_id, _ in device_requests)
    assert all(secret == "service-secret" for _, _, _, secret in device_requests)


def test_gateway_reads_service_secret_from_fallback_env_file(tmp_path) -> None:
    fallback_file = tmp_path / "hub.env"
    fallback_file.write_text(
        "ASSISTANT_SERVICE_ID=assistant-runtime\nASSISTANT_SERVICE_SECRET=fallback-secret\n",
        encoding="utf-8",
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/devices":
            assert request.headers.get("x-alice-service-id") == "assistant-runtime"
            assert request.headers.get("x-alice-service-secret") == "fallback-secret"
            return httpx.Response(200, json={"items": []})
        raise AssertionError(f"Unexpected request path: {request.url.path}")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    gateway = HomeOsGateway(
        Settings(
            home_os_base_url="http://alice.local/api/v1",
            home_os_service_secret=None,
            home_os_env_fallback_file=str(fallback_file),
        ),
        client=client,
    )

    async def run() -> None:
        devices = await gateway.list_devices()
        assert devices == []
        await client.aclose()

    asyncio.run(run())
