from __future__ import annotations

from dataclasses import dataclass

from assistant_runtime.clients.home_os_gateway import HomeOsGateway
from assistant_runtime.models import Device, Entity, EntityState
from assistant_runtime.schemas import ChatResponse, ToolTrace


@dataclass
class AssistantContext:
    devices: list[Device]
    entities: list[Entity]
    states: list[EntityState]


class AssistantService:
    def __init__(self, gateway: HomeOsGateway) -> None:
        self.gateway = gateway

    async def chat(self, message: str) -> ChatResponse:
        lowered = " ".join(message.lower().split())
        traces: list[ToolTrace] = []

        if any(phrase in lowered for phrase in ("stack health", "system health", "hub health")):
            health = await self.gateway.get_stack_health()
            traces.append(ToolTrace(tool="system.stack_health", status="ok", detail="Fetched stack health"))
            broker = health["broker"]
            devices = health["devices"]
            reply = (
                f"API is {health['api_status']}. "
                f"Broker is {'connected' if broker['connected'] else 'disconnected'} at {broker['host']}:{broker['port']}. "
                f"Devices: {devices['online']} online, {devices['offline']} offline."
            )
            return ChatResponse(mode="deterministic", success=True, reply=reply, tool_traces=traces)

        context = await self._load_context(traces)

        if any(phrase in lowered for phrase in ("devices online", "what devices are online", "which devices are online")):
            online = [device.name for device in context.devices if device.status == "online"]
            if not online:
                reply = "No devices are currently online."
            else:
                reply = f"Online devices: {', '.join(online)}."
            return ChatResponse(mode="deterministic", success=True, reply=reply, tool_traces=traces)

        if "temperature" in lowered or "temp" in lowered:
            matches = self._states_for_kind(context, "sensor.temperature")
            if not matches:
                return ChatResponse(
                    mode="deterministic",
                    success=False,
                    reply="I could not find any temperature entities in Home OS.",
                    tool_traces=traces,
                )
            parts = []
            for entity, state in matches:
                value = state.value.get("celsius")
                if value is not None:
                    parts.append(f"{entity.name}: {value} C")
            reply = "Current temperature readings: " + ", ".join(parts) + "."
            return ChatResponse(mode="deterministic", success=True, reply=reply, tool_traces=traces)

        if any(term in lowered for term in ("light level", "brightness", "lux", "illuminance")):
            matches = self._states_for_kind(context, "sensor.illuminance")
            if not matches:
                return ChatResponse(
                    mode="deterministic",
                    success=False,
                    reply="I could not find any illuminance entities in Home OS.",
                    tool_traces=traces,
                )
            parts = []
            for entity, state in matches:
                lux = state.value.get("lux")
                raw = state.value.get("raw")
                if lux is not None:
                    parts.append(f"{entity.name}: {lux} lux (raw {raw})")
            reply = "Current light readings: " + ", ".join(parts) + "."
            return ChatResponse(mode="deterministic", success=True, reply=reply, tool_traces=traces)

        if any(term in lowered for term in ("turn on", "switch on", "light on")):
            target = self._find_relay_entity(context, lowered)
            if target is None:
                return ChatResponse(
                    mode="deterministic",
                    success=False,
                    reply="I could not find a writable relay/light entity to turn on.",
                    tool_traces=traces,
                )
            result = await self.gateway.execute_entity_command(
                entity_id=target.id,
                command="switch.set",
                params={"on": True},
            )
            traces.append(ToolTrace(tool="entities.command", status="ok", detail=f"Turned on {target.name}"))
            return ChatResponse(
                mode="deterministic",
                success=True,
                reply=f"Queued turn-on command for {target.name}. Topic: {result['topic']}.",
                tool_traces=traces,
            )

        if any(term in lowered for term in ("turn off", "switch off", "light off")):
            target = self._find_relay_entity(context, lowered)
            if target is None:
                return ChatResponse(
                    mode="deterministic",
                    success=False,
                    reply="I could not find a writable relay/light entity to turn off.",
                    tool_traces=traces,
                )
            result = await self.gateway.execute_entity_command(
                entity_id=target.id,
                command="switch.set",
                params={"on": False},
            )
            traces.append(ToolTrace(tool="entities.command", status="ok", detail=f"Turned off {target.name}"))
            return ChatResponse(
                mode="deterministic",
                success=True,
                reply=f"Queued turn-off command for {target.name}. Topic: {result['topic']}.",
                tool_traces=traces,
            )

        return ChatResponse(
            mode="deterministic",
            success=False,
            reply=(
                "I can currently list online devices, report temperature or light readings, "
                "show stack health, and turn the light relay on or off."
            ),
            tool_traces=traces,
        )

    async def _load_context(self, traces: list[ToolTrace]) -> AssistantContext:
        devices = await self.gateway.list_devices()
        traces.append(ToolTrace(tool="devices.list", status="ok", detail=f"Loaded {len(devices)} devices"))
        entities = await self.gateway.list_entities()
        traces.append(ToolTrace(tool="entities.list", status="ok", detail=f"Loaded {len(entities)} entities"))
        states = await self.gateway.list_entity_states()
        traces.append(ToolTrace(tool="entities.states", status="ok", detail=f"Loaded {len(states)} states"))
        return AssistantContext(devices=devices, entities=entities, states=states)

    def _states_for_kind(self, context: AssistantContext, kind: str) -> list[tuple[Entity, EntityState]]:
        state_map = {state.entity_id: state for state in context.states}
        matches: list[tuple[Entity, EntityState]] = []
        for entity in context.entities:
            if entity.kind != kind:
                continue
            state = state_map.get(entity.id)
            if state is not None:
                matches.append((entity, state))
        return matches

    def _find_relay_entity(self, context: AssistantContext, lowered_message: str) -> Entity | None:
        writable_relays = [
            entity
            for entity in context.entities
            if entity.writable == 1 and entity.kind == "switch.relay"
        ]
        if not writable_relays:
            return None

        for entity in writable_relays:
            if entity.name.lower() in lowered_message:
                return entity
            if entity.capability_id.lower() in lowered_message:
                return entity
        return writable_relays[0]
