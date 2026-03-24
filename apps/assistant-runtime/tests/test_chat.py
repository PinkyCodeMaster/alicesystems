from __future__ import annotations

import asyncio

from assistant_runtime.core.config import Settings
from assistant_runtime.models import AuditEvent, AutoLightSettings, Device, DeviceDetail, DeviceDetailEntity, Entity, EntityState, SessionMessage
from assistant_runtime.schemas import ChatResponse
from assistant_runtime.services.assistant_service import AssistantService
from assistant_runtime.services.ollama_planner import PlannerDecision
from assistant_runtime.services.session_store import SessionStore


class FakeGateway:
    def __init__(self) -> None:
        self.last_command: tuple[str, str, dict] | None = None
        self.last_auto_light_update: dict | None = None
        self.auto_light_settings = AutoLightSettings(
            enabled=True,
            sensor_entity_id="ent_dev_sensor_hall_01_illuminance",
            target_entity_id="ent_dev_light_bench_01_relay",
            mode="raw_high_turn_on",
            on_lux=50.0,
            off_lux=35.0,
            on_raw=3000.0,
            off_raw=2600.0,
            block_on_during_daytime=True,
            daytime_start_hour=7,
            daytime_end_hour=18,
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
        self.device_details = {
            "dev_light_bench_01": DeviceDetail(
                device=Device(
                    id="dev_light_bench_01",
                    name="Bench Light",
                    device_type="relay_node",
                    status="online",
                    fw_version="0.1.1",
                ),
                entities=[
                    DeviceDetailEntity(
                        id="ent_dev_light_bench_01_relay",
                        capability_id="relay",
                        kind="switch.relay",
                        name="Bench Light",
                        writable=1,
                        state={"on": True},
                        state_source="mqtt.state",
                        state_updated_at="2026-03-23T18:01:02",
                        state_version=3,
                    )
                ],
                audit_events=self.audit_events,
            ),
            "dev_sensor_hall_01": DeviceDetail(
                device=Device(
                    id="dev_sensor_hall_01",
                    name="Hall Sensor",
                    device_type="sensor_node",
                    status="online",
                    fw_version="0.1.1",
                ),
                entities=[
                    DeviceDetailEntity(
                        id="ent_dev_sensor_hall_01_illuminance",
                        capability_id="illuminance",
                        kind="sensor.illuminance",
                        name="Hall Sensor Illuminance",
                        writable=0,
                        state={"lux": 42.0, "raw": 2900},
                        state_source="mqtt.state",
                        state_updated_at="2026-03-23T18:00:00",
                        state_version=2,
                    ),
                    DeviceDetailEntity(
                        id="ent_dev_sensor_hall_01_temperature",
                        capability_id="temperature",
                        kind="sensor.temperature",
                        name="Hall Sensor Temperature",
                        writable=0,
                        state={"celsius": 23.4},
                        state_source="mqtt.state",
                        state_updated_at="2026-03-23T18:00:00",
                        state_version=1,
                    ),
                ],
                audit_events=[],
            ),
        }

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
                id="ent_dev_sensor_hall_01_illuminance",
                device_id="dev_sensor_hall_01",
                capability_id="illuminance",
                kind="sensor.illuminance",
                name="Hall Sensor Illuminance",
                writable=0,
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
                entity_id="ent_dev_sensor_hall_01_illuminance",
                value={"lux": 42.0, "raw": 2900},
                source="mqtt.state",
                updated_at="2026-03-23T18:00:00",
                version=1,
            ),
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

    async def get_device_detail(self, *, device_id: str):
        return self.device_details[device_id]

    async def get_auto_light_settings(self):
        return self.auto_light_settings

    async def update_auto_light_enabled(self, *, enabled: bool):
        self.auto_light_settings.enabled = enabled
        return self.auto_light_settings

    async def update_auto_light_settings(self, **changes):
        self.last_auto_light_update = changes
        for key, value in changes.items():
            setattr(self.auto_light_settings, key, value)
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

    async def chat(
        self,
        *,
        recent_messages: list[SessionMessage],
        devices: list[Device],
        entities: list[Entity],
        states: list[EntityState],
    ) -> str:
        return "Hello from planner chat."


class FakeThresholdPlanner:
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
            action="update_auto_light_thresholds",
            reply="Planner updated the auto-light thresholds.",
            params={"on_raw": 3300.0, "off_raw": 2800.0},
        )

    async def chat(
        self,
        *,
        recent_messages: list[SessionMessage],
        devices: list[Device],
        entities: list[Entity],
        states: list[EntityState],
    ) -> str:
        return "Hello from planner chat."


class FakeMappingPlanner:
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
            action="update_auto_light_mapping",
            reply="Planner updated the auto-light mapping.",
            params={
                "sensor_entity_id": "ent_dev_sensor_hall_01_illuminance",
                "target_entity_id": "ent_dev_light_bench_01_relay",
            },
        )

    async def chat(
        self,
        *,
        recent_messages: list[SessionMessage],
        devices: list[Device],
        entities: list[Entity],
        states: list[EntityState],
    ) -> str:
        return "Hello from planner chat."


class FakeDeviceDetailPlanner:
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
            action="show_device_detail",
            reply="Planner loaded the bench light details.",
            target_hint="Bench Light",
        )

    async def chat(
        self,
        *,
        recent_messages: list[SessionMessage],
        devices: list[Device],
        entities: list[Entity],
        states: list[EntityState],
    ) -> str:
        return "Hello from planner chat."


class FakeConversationPlanner:
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
        return PlannerDecision(action="none")

    async def chat(
        self,
        *,
        recent_messages: list[SessionMessage],
        devices: list[Device],
        entities: list[Entity],
        states: list[EntityState],
    ) -> str:
        assert recent_messages[-1].content == "hello alice"
        return "Hey, I'm here. What do you want to work on in the house today?"

    async def stream_chat(
        self,
        *,
        recent_messages: list[SessionMessage],
        devices: list[Device],
        entities: list[Entity],
        states: list[EntityState],
    ):
        assert recent_messages[-1].content == "hello alice"
        for chunk in ("Hey, ", "I'm here. ", "What do you want to work on in the house today?"):
            yield chunk


class FailingConversationPlanner:
    def __init__(self) -> None:
        self.chat_called = False

    async def plan(
        self,
        *,
        message: str,
        recent_messages: list[SessionMessage],
        devices: list[Device],
        entities: list[Entity],
        states: list[EntityState],
    ) -> PlannerDecision:
        raise RuntimeError("planner failed")

    async def chat(
        self,
        *,
        recent_messages: list[SessionMessage],
        devices: list[Device],
        entities: list[Entity],
        states: list[EntityState],
    ) -> str:
        self.chat_called = True
        return "Hi. I can chat normally, and I can still help with your devices when you need that."

    async def stream_chat(
        self,
        *,
        recent_messages: list[SessionMessage],
        devices: list[Device],
        entities: list[Entity],
        states: list[EntityState],
    ):
        self.chat_called = True
        yield "Hi. "
        yield "I can chat normally, and I can still help with your devices when you need that."


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


async def _collect_stream(
    service: AssistantService,
    message: str,
    session_id: str | None = None,
):
    return [event async for event in service.chat_stream(message=message, session_id=session_id)]


def test_reports_online_devices(tmp_path):
    service = build_service(tmp_path)
    response = asyncio.run(_chat(service, "what devices are online"))
    assert response.success is True
    assert "Bench Light" in response.reply
    assert response.session_id.startswith("sess_")


def test_reports_device_detail(tmp_path):
    service = build_service(tmp_path)
    response = asyncio.run(_chat(service, "show me the bench light details"))
    assert response.success is True
    assert "Bench Light is online" in response.reply
    assert "Bench Light: on=True" in response.reply
    assert "entity.command.requested" in response.reply


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
    assert "Daytime block: on" in response.reply


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


def test_can_update_single_auto_light_threshold(tmp_path):
    service = build_service(tmp_path)
    response = asyncio.run(_chat(service, "set auto-light on raw to 3200"))
    assert response.success is True
    assert "Updated auto-light thresholds." in response.reply
    assert service.gateway.last_auto_light_update == {"on_raw": 3200.0}
    assert service.gateway.auto_light_settings.on_raw == 3200.0


def test_can_update_multiple_auto_light_thresholds(tmp_path):
    service = build_service(tmp_path)
    response = asyncio.run(_chat(service, "set auto light on lux to 60 and off lux to 40"))
    assert response.success is True
    assert service.gateway.last_auto_light_update == {"on_lux": 60.0, "off_lux": 40.0}
    assert service.gateway.auto_light_settings.on_lux == 60.0
    assert service.gateway.auto_light_settings.off_lux == 40.0


def test_can_update_auto_light_sensor_mapping(tmp_path):
    service = build_service(tmp_path)
    response = asyncio.run(_chat(service, "set auto-light sensor to hall sensor illuminance"))
    assert response.success is True
    assert response.reply.startswith("Updated auto-light mapping.")
    assert service.gateway.last_auto_light_update == {"sensor_entity_id": "ent_dev_sensor_hall_01_illuminance"}


def test_can_update_auto_light_target_mapping(tmp_path):
    service = build_service(tmp_path)
    response = asyncio.run(_chat(service, "set auto light target to bench light"))
    assert response.success is True
    assert service.gateway.last_auto_light_update == {"target_entity_id": "ent_dev_light_bench_01_relay"}


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


def test_ollama_planner_can_update_auto_light_thresholds(tmp_path):
    service = build_service(tmp_path, assistant_mode="auto", planner=FakeThresholdPlanner())
    response = asyncio.run(_chat(service, "make auto-light less sensitive"))
    assert response.mode == "ollama"
    assert response.success is True
    assert response.reply == "Planner updated the auto-light thresholds."
    assert service.gateway.last_auto_light_update == {"on_raw": 3300.0, "off_raw": 2800.0}


def test_ollama_planner_can_update_auto_light_mapping(tmp_path):
    service = build_service(tmp_path, assistant_mode="auto", planner=FakeMappingPlanner())
    response = asyncio.run(_chat(service, "use the hall sensor for auto light"))
    assert response.mode == "ollama"
    assert response.success is True
    assert response.reply == "Planner updated the auto-light mapping."
    assert service.gateway.last_auto_light_update == {
        "sensor_entity_id": "ent_dev_sensor_hall_01_illuminance",
        "target_entity_id": "ent_dev_light_bench_01_relay",
    }


def test_ollama_planner_can_show_device_detail(tmp_path):
    service = build_service(tmp_path, assistant_mode="auto", planner=FakeDeviceDetailPlanner())
    response = asyncio.run(_chat(service, "what's going on with the bench light"))
    assert response.mode == "ollama"
    assert response.success is True
    assert response.reply == "Planner loaded the bench light details."


def test_ollama_can_reply_naturally_when_no_tool_action_is_needed(tmp_path):
    service = build_service(tmp_path, assistant_mode="auto", planner=FakeConversationPlanner())
    response = asyncio.run(_chat(service, "hello alice"))
    assert response.mode == "ollama"
    assert response.success is True
    assert response.reply == "Hey, I'm here. What do you want to work on in the house today?"
    assert any(trace.tool == "chat.ollama" and trace.status == "ok" for trace in response.tool_traces)


def test_ollama_chat_fallback_runs_when_planner_fails_for_plain_conversation(tmp_path):
    planner = FailingConversationPlanner()
    service = build_service(tmp_path, assistant_mode="auto", planner=planner)
    response = asyncio.run(_chat(service, "hello alice"))
    assert response.mode == "ollama"
    assert response.success is True
    assert planner.chat_called is True
    assert response.reply.startswith("Hi. I can chat normally")


def test_tool_commands_still_fall_back_to_deterministic_execution_when_planner_fails(tmp_path):
    planner = FailingConversationPlanner()
    service = build_service(tmp_path, assistant_mode="auto", planner=planner)
    response = asyncio.run(_chat(service, "turn on the bench light"))
    assert response.mode == "deterministic"
    assert response.success is True
    assert planner.chat_called is False
    assert service.gateway.last_command == (
        "ent_dev_light_bench_01_relay",
        "switch.set",
        {"on": True},
    )


def test_streaming_conversation_emits_deltas_and_done(tmp_path):
    service = build_service(tmp_path, assistant_mode="auto", planner=FakeConversationPlanner())
    events = asyncio.run(_collect_stream(service, "hello alice"))
    assert events[0]["event"] == "start"
    assert events[1]["event"] == "delta"
    assert events[-1]["event"] == "done"
    done = events[-1]["data"]
    assert done["mode"] == "ollama"
    assert done["success"] is True
    assert "What do you want to work on" in done["reply"]


def test_streaming_tool_reply_emits_done_and_persists_session(tmp_path):
    service = build_service(tmp_path)
    events = asyncio.run(_collect_stream(service, "turn on the bench light"))
    assert events[0]["event"] == "start"
    assert events[-1]["event"] == "done"
    done = events[-1]["data"]
    assert done["mode"] == "deterministic"
    assert done["success"] is True
    messages = asyncio.run(service.list_messages(session_id=done["session_id"]))
    assert messages[-1].role == "assistant"
    assert "Queued turn-on command" in messages[-1].content
