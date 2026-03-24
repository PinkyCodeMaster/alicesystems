from __future__ import annotations

import asyncio

from assistant_runtime.core.config import Settings
from assistant_runtime.models import AuditEvent, AutoLightSettings, Device, Entity, EntityState, SessionMessage
from assistant_runtime.schemas import ChatResponse
from assistant_runtime.services.assistant_service import AssistantService
from assistant_runtime.services.ollama_planner import PlannerDecision
from assistant_runtime.services.session_store import SessionStore


class FakeGateway:
    def __init__(self) -> None:
        self.last_command: tuple[str, str, dict] | None = None
        self.auto_light_settings = AutoLightSettings(
            enabled=True,
            sensor_entity_id="ent_dev_sensor_hall_01_illuminance",
            target_entity_id="ent_dev_light_bench_01_relay",
            mode="raw_high_turn_on",
            on_lux=50.0,
            off_lux=35.0,
            on_raw=3000.0,
            off_raw=2600.0,
            source="sqlite",
            updated_at="2026-03-23T18:00:00",
        )
        self.audit_events = [
            AuditEvent(
                id="audit_1",
                actor_type="system",
                actor_id="system:auto-light",
                action="entity.command.requested",
                target_type="entity",
                target_id="ent_dev_light_bench_01_relay",
                severity="info",
                metadata_json="{}",
                created_at="2026-03-23T18:01:00",
            ),
            AuditEvent(
                id="audit_2",
                actor_type="device",
                actor_id="dev_light_bench_01",
                action="device.ack.received",
                target_type="device",
                target_id="dev_light_bench_01",
                severity="info",
                metadata_json="{}",
                created_at="2026-03-23T18:01:02",
            ),
        ]

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

    async def get_auto_light_settings(self):
        return self.auto_light_settings

    async def update_auto_light_enabled(self, *, enabled: bool):
        self.auto_light_settings.enabled = enabled
        return self.auto_light_settings

    async def list_audit_events(self, *, limit: int = 5):
        return self.audit_events[:limit]

    async def execute_entity_command(self, *, entity_id: str, command: str, params: dict):
        self.last_command = (entity_id, command, params)
        return {"topic": "alice/v1/device/dev_light_bench_01/cmd"}


class FakePlanner:
    async def plan(
        self,
        *,
        message: str,
        recent_messages: list[SessionMessage],
        devices: list[Device],
        entities: list[Entity],
        states: list[EntityState],
    ) -> PlannerDecision:
        assert recent_messages
        return PlannerDecision(
            action="turn_light_off",
            reply="Planner chose to turn the bench light off.",
            target_hint="Bench Light",
        )


def build_service(tmp_path, *, assistant_mode: str = "deterministic", planner=None) -> AssistantService:
    settings = Settings(
        assistant_mode=assistant_mode,
        ollama_model="qwen2.5:3b",
        session_store_file=str(tmp_path / "assistant.db"),
    )
    store = SessionStore(settings.session_store_path)
    return AssistantService(
        gateway=FakeGateway(),
        settings=settings,
        store=store,
        planner=planner,
    )


async def _chat(service: AssistantService, message: str, session_id: str | None = None) -> ChatResponse:
    return await service.chat(message=message, session_id=session_id)


def test_reports_online_devices(tmp_path):
    service = build_service(tmp_path)
    response = asyncio.run(_chat(service, "what devices are online"))
    assert response.success is True
    assert "Bench Light" in response.reply
    assert response.session_id.startswith("sess_")


def test_reports_temperature(tmp_path):
    service = build_service(tmp_path)
    response = asyncio.run(_chat(service, "what is the temperature"))
    assert response.success is True
    assert "23.4 C" in response.reply


def test_turns_light_on(tmp_path):
    service = build_service(tmp_path)
    response = asyncio.run(_chat(service, "turn on the bench light"))
    assert response.success is True
    assert service.gateway.last_command == (
        "ent_dev_light_bench_01_relay",
        "switch.set",
        {"on": True},
    )


def test_reports_auto_light_status(tmp_path):
    service = build_service(tmp_path)
    response = asyncio.run(_chat(service, "is auto-light enabled"))
    assert response.success is True
    assert "Auto-light is enabled." in response.reply
    assert "raw_high_turn_on" in response.reply


def test_can_disable_auto_light(tmp_path):
    service = build_service(tmp_path)
    response = asyncio.run(_chat(service, "turn off auto light"))
    assert response.success is True
    assert response.reply.startswith("Auto-light is now disabled.")
    assert service.gateway.auto_light_settings.enabled is False


def test_lists_recent_audit_events(tmp_path):
    service = build_service(tmp_path)
    response = asyncio.run(_chat(service, "what happened recently"))
    assert response.success is True
    assert "entity.command.requested" in response.reply
    assert "device.ack.received" in response.reply


def test_persists_session_history(tmp_path):
    service = build_service(tmp_path)
    first = asyncio.run(_chat(service, "what devices are online"))
    second = asyncio.run(_chat(service, "what is the temperature", session_id=first.session_id))
    messages = asyncio.run(service.list_messages(session_id=second.session_id))
    assert len(messages) == 4
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"
    assert messages[2].role == "user"
    assert messages[3].role == "assistant"


def test_ollama_planner_can_choose_action(tmp_path):
    service = build_service(tmp_path, assistant_mode="auto", planner=FakePlanner())
    response = asyncio.run(_chat(service, "turn it off"))
    assert response.mode == "ollama"
    assert response.success is True
    assert response.reply == "Planner chose to turn the bench light off."
    assert service.gateway.last_command == (
        "ent_dev_light_bench_01_relay",
        "switch.set",
        {"on": False},
    )
