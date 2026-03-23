from __future__ import annotations

import asyncio

from assistant_runtime.models import Device, Entity, EntityState
from assistant_runtime.schemas import ChatResponse
from assistant_runtime.services.assistant_service import AssistantService


class FakeGateway:
    def __init__(self) -> None:
        self.last_command: tuple[str, str, dict] | None = None

    async def list_devices(self):
        return [
            Device(id="dev_light_bench_01", name="Bench Light", device_type="relay_node", status="online", fw_version="0.1.1"),
            Device(id="dev_sensor_hall_01", name="Hall Sensor", device_type="sensor_node", status="online", fw_version="0.1.1"),
        ]

    async def list_entities(self):
        return [
            Entity(
                id="ent_dev_light_bench_01_relay",
                device_id="dev_light_bench_01",
                capability_id="relay",
                kind="switch.relay",
                name="Bench Light",
                writable=1,
            ),
            Entity(
                id="ent_dev_sensor_hall_01_temperature",
                device_id="dev_sensor_hall_01",
                capability_id="temperature",
                kind="sensor.temperature",
                name="Hall Sensor Temperature",
                writable=0,
            ),
        ]

    async def list_entity_states(self):
        return [
            EntityState(
                entity_id="ent_dev_sensor_hall_01_temperature",
                value={"celsius": 23.4},
                source="mqtt.state",
                updated_at="2026-03-23T18:00:00",
                version=1,
            )
        ]

    async def get_stack_health(self):
        return {
            "api_status": "ok",
            "broker": {"connected": True, "host": "127.0.0.1", "port": 1883},
            "devices": {"online": 2, "offline": 0},
        }

    async def execute_entity_command(self, *, entity_id: str, command: str, params: dict):
        self.last_command = (entity_id, command, params)
        return {"topic": "alice/v1/device/dev_light_bench_01/cmd"}


async def _chat(message: str) -> ChatResponse:
    service = AssistantService(FakeGateway())
    return await service.chat(message)


def test_reports_online_devices():
    response = asyncio.run(_chat("what devices are online"))
    assert response.success is True
    assert "Bench Light" in response.reply


def test_reports_temperature():
    response = asyncio.run(_chat("what is the temperature"))
    assert response.success is True
    assert "23.4 C" in response.reply


def test_turns_light_on():
    gateway = FakeGateway()
    service = AssistantService(gateway)
    response = asyncio.run(service.chat("turn on the bench light"))
    assert response.success is True
    assert gateway.last_command == (
        "ent_dev_light_bench_01_relay",
        "switch.set",
        {"on": True},
    )
