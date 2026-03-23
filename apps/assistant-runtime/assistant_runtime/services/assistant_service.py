from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from assistant_runtime.clients.home_os_gateway import HomeOsGateway
from assistant_runtime.core.config import Settings
from assistant_runtime.models import Device, Entity, EntityState, SessionMessage
from assistant_runtime.schemas import ChatDebug, ChatResponse, DependencyStatus, ToolTrace
from assistant_runtime.services.ollama_planner import OllamaPlanner, PlannerDecision
from assistant_runtime.services.session_store import SessionStore


@dataclass
class AssistantContext:
    devices: list[Device]
    entities: list[Entity]
    states: list[EntityState]


class Planner(Protocol):
    async def plan(
        self,
        *,
        message: str,
        recent_messages: list[SessionMessage],
        devices: list[Device],
        entities: list[Entity],
        states: list[EntityState],
    ) -> PlannerDecision: ...


class AssistantService:
    def __init__(
        self,
        gateway: HomeOsGateway,
        settings: Settings,
        store: SessionStore,
        planner: Planner | None = None,
    ) -> None:
        self.gateway = gateway
        self.settings = settings
        self.store = store
        self.planner = planner or OllamaPlanner(settings)

    async def health_dependencies(self) -> dict[str, DependencyStatus]:
        dependencies: dict[str, DependencyStatus] = {}

        try:
            await self.gateway.get_stack_health()
            dependencies["home_os"] = DependencyStatus(
                reachable=True,
                detail=f"Reachable at {self.settings.home_os_base_url}.",
            )
        except Exception as exc:
            dependencies["home_os"] = DependencyStatus(
                reachable=False,
                detail=str(exc),
            )

        if self.settings.assistant_mode in {"auto", "ollama"}:
            try:
                reachable, detail = await self.planner.health()
                dependencies["ollama"] = DependencyStatus(reachable=reachable, detail=detail)
            except Exception as exc:
                dependencies["ollama"] = DependencyStatus(reachable=False, detail=str(exc))
        else:
            dependencies["ollama"] = DependencyStatus(
                reachable=False,
                detail="Assistant is running in deterministic mode.",
            )

        return dependencies

    async def chat(self, *, message: str, session_id: str | None = None) -> ChatResponse:
        session_id = self.store.ensure_session(session_id)
        self.store.append_message(session_id=session_id, role="user", content=message)

        lowered = " ".join(message.lower().split())
        traces: list[ToolTrace] = []
        recent_messages = self.store.list_messages(
            session_id=session_id,
            limit=max(2, self.settings.session_history_window * 2),
        )

        mode = "deterministic"
        context: AssistantContext | None = None
        planner_reply: str | None = None
        planner_action: str | None = None
        planner_target_hint: str | None = None
        planner_source = "deterministic"
        fallback_used = False
        planner_error: str | None = None

        if self.settings.assistant_mode in {"auto", "ollama"}:
            try:
                context = await self._load_context(traces)
                decision = await self.planner.plan(
                    message=message,
                    recent_messages=recent_messages,
                    devices=context.devices,
                    entities=context.entities,
                    states=context.states,
                )
                traces.append(ToolTrace(tool="planner.ollama", status="ok", detail=f"Planned action {decision.action}"))
                mode = "ollama"
                planner_source = "ollama"
                planner_reply = decision.reply
                planner_action = decision.action
                planner_target_hint = decision.target_hint
            except Exception as exc:
                if self.settings.assistant_mode == "ollama" and not self.settings.assistant_allow_fallback:
                    raise
                fallback_used = True
                planner_error = str(exc)
                traces.append(ToolTrace(tool="planner.ollama", status="fallback", detail=str(exc)))

        if planner_action:
            response = await self._execute_action(
                action=planner_action,
                lowered_message=lowered,
                traces=traces,
                mode=mode,
                context=context,
                planner_reply=planner_reply,
                planner_target_hint=planner_target_hint,
            )
        else:
            response = await self._execute_action(
                action=self._infer_deterministic_action(lowered),
                lowered_message=lowered,
                traces=traces,
                mode="deterministic",
                context=context,
                planner_reply=None,
                planner_target_hint=None,
            )

        response.debug = self._build_debug(
            response_mode=response.mode,
            planner_source=planner_source,
            fallback_used=fallback_used,
            planner_error=planner_error,
        )

        self.store.append_message(
            session_id=session_id,
            role="assistant",
            content=response.reply,
            mode=response.mode,
            success=response.success,
            metadata={
                "tool_traces": [trace.model_dump() for trace in response.tool_traces],
                "debug": response.debug.model_dump(),
            },
        )
        return ChatResponse(
            session_id=session_id,
            mode=response.mode,
            success=response.success,
            reply=response.reply,
            tool_traces=response.tool_traces,
            debug=response.debug,
        )

    async def list_messages(self, *, session_id: str) -> list[SessionMessage]:
        self.store.ensure_session(session_id)
        return self.store.list_messages(session_id=session_id)

    async def _execute_action(
        self,
        *,
        action: str,
        lowered_message: str,
        traces: list[ToolTrace],
        mode: str,
        context: AssistantContext | None,
        planner_reply: str | None,
        planner_target_hint: str | None,
    ) -> ChatResponse:
        if action == "stack_health":
            health = await self.gateway.get_stack_health()
            traces.append(ToolTrace(tool="system.stack_health", status="ok", detail="Fetched stack health"))
            broker = health["broker"]
            devices = health["devices"]
            reply = planner_reply or (
                f"API is {health['api_status']}. "
                f"Broker is {'connected' if broker['connected'] else 'disconnected'} at {broker['host']}:{broker['port']}. "
                f"Devices: {devices['online']} online, {devices['offline']} offline."
            )
            return ChatResponse(
                session_id="",
                mode=mode,
                success=True,
                reply=reply,
                tool_traces=traces,
                debug=self._build_debug(
                    response_mode=mode,
                    planner_source=("ollama" if mode == "ollama" else "deterministic"),
                    fallback_used=False,
                    planner_error=None,
                ),
            )

        context = context or await self._load_context(traces)

        if action == "list_online_devices":
            online = [device.name for device in context.devices if device.status == "online"]
            reply = planner_reply or ("No devices are currently online." if not online else f"Online devices: {', '.join(online)}.")
            return ChatResponse(
                session_id="",
                mode=mode,
                success=True,
                reply=reply,
                tool_traces=traces,
                debug=self._build_debug(
                    response_mode=mode,
                    planner_source=("ollama" if mode == "ollama" else "deterministic"),
                    fallback_used=False,
                    planner_error=None,
                ),
            )

        if action == "report_temperature":
            matches = self._states_for_kind(context, "sensor.temperature")
            if not matches:
                return ChatResponse(
                    session_id="",
                    mode=mode,
                    success=False,
                    reply="I could not find any temperature entities in Home OS.",
                    tool_traces=traces,
                    debug=self._build_debug(
                        response_mode=mode,
                        planner_source=("ollama" if mode == "ollama" else "deterministic"),
                        fallback_used=False,
                        planner_error=None,
                    ),
                )
            parts = [f"{entity.name}: {state.value.get('celsius')} C" for entity, state in matches if state.value.get("celsius") is not None]
            reply = planner_reply or ("Current temperature readings: " + ", ".join(parts) + ".")
            return ChatResponse(
                session_id="",
                mode=mode,
                success=True,
                reply=reply,
                tool_traces=traces,
                debug=self._build_debug(
                    response_mode=mode,
                    planner_source=("ollama" if mode == "ollama" else "deterministic"),
                    fallback_used=False,
                    planner_error=None,
                ),
            )

        if action == "report_illuminance":
            matches = self._states_for_kind(context, "sensor.illuminance")
            if not matches:
                return ChatResponse(
                    session_id="",
                    mode=mode,
                    success=False,
                    reply="I could not find any illuminance entities in Home OS.",
                    tool_traces=traces,
                    debug=self._build_debug(
                        response_mode=mode,
                        planner_source=("ollama" if mode == "ollama" else "deterministic"),
                        fallback_used=False,
                        planner_error=None,
                    ),
                )
            parts = [
                f"{entity.name}: {state.value.get('lux')} lux (raw {state.value.get('raw')})"
                for entity, state in matches
                if state.value.get("lux") is not None
            ]
            reply = planner_reply or ("Current light readings: " + ", ".join(parts) + ".")
            return ChatResponse(
                session_id="",
                mode=mode,
                success=True,
                reply=reply,
                tool_traces=traces,
                debug=self._build_debug(
                    response_mode=mode,
                    planner_source=("ollama" if mode == "ollama" else "deterministic"),
                    fallback_used=False,
                    planner_error=None,
                ),
            )

        if action in {"turn_light_on", "turn_light_off"}:
            target = self._find_relay_entity(
                context=context,
                lowered_message=lowered_message,
                target_hint=planner_target_hint,
            )
            if target is None:
                return ChatResponse(
                    session_id="",
                    mode=mode,
                    success=False,
                    reply=f"I could not find a writable relay/light entity to {action.replace('_', ' ')}.",
                    tool_traces=traces,
                    debug=self._build_debug(
                        response_mode=mode,
                        planner_source=("ollama" if mode == "ollama" else "deterministic"),
                        fallback_used=False,
                        planner_error=None,
                    ),
                )
            should_turn_on = action == "turn_light_on"
            result = await self.gateway.execute_entity_command(
                entity_id=target.id,
                command="switch.set",
                params={"on": should_turn_on},
            )
            traces.append(
                ToolTrace(
                    tool="entities.command",
                    status="ok",
                    detail=f"{'Turned on' if should_turn_on else 'Turned off'} {target.name}",
                )
            )
            reply = planner_reply or (
                f"Queued {'turn-on' if should_turn_on else 'turn-off'} command for {target.name}. "
                f"Topic: {result['topic']}."
            )
            return ChatResponse(
                session_id="",
                mode=mode,
                success=True,
                reply=reply,
                tool_traces=traces,
                debug=self._build_debug(
                    response_mode=mode,
                    planner_source=("ollama" if mode == "ollama" else "deterministic"),
                    fallback_used=False,
                    planner_error=None,
                ),
            )

        return ChatResponse(
            session_id="",
            mode="deterministic" if mode != "ollama" else mode,
            success=False,
            reply=(
                "I can currently list online devices, report temperature or light readings, "
                "show stack health, and turn the light relay on or off."
            ),
            tool_traces=traces,
            debug=self._build_debug(
                response_mode=("deterministic" if mode != "ollama" else mode),
                planner_source=("ollama" if mode == "ollama" else "deterministic"),
                fallback_used=False,
                planner_error=None,
            ),
        )

    def _build_debug(
        self,
        *,
        response_mode: str,
        planner_source: str,
        fallback_used: bool,
        planner_error: str | None,
    ) -> ChatDebug:
        return ChatDebug(
            configured_mode=self.settings.assistant_mode,
            response_mode=response_mode,
            planner_source=planner_source,
            fallback_used=fallback_used,
            ollama_configured=bool(self.settings.ollama_model),
            ollama_model=self.settings.ollama_model,
            planner_error=planner_error,
            home_os_base_url=self.settings.home_os_base_url,
        )

    async def _load_context(self, traces: list[ToolTrace]) -> AssistantContext:
        devices = await self.gateway.list_devices()
        traces.append(ToolTrace(tool="devices.list", status="ok", detail=f"Loaded {len(devices)} devices"))
        entities = await self.gateway.list_entities()
        traces.append(ToolTrace(tool="entities.list", status="ok", detail=f"Loaded {len(entities)} entities"))
        states = await self.gateway.list_entity_states()
        traces.append(ToolTrace(tool="entities.states", status="ok", detail=f"Loaded {len(states)} states"))
        return AssistantContext(devices=devices, entities=entities, states=states)

    def _infer_deterministic_action(self, lowered: str) -> str:
        if any(phrase in lowered for phrase in ("stack health", "system health", "hub health")):
            return "stack_health"
        if any(phrase in lowered for phrase in ("devices online", "what devices are online", "which devices are online")):
            return "list_online_devices"
        if "temperature" in lowered or "temp" in lowered:
            return "report_temperature"
        if any(term in lowered for term in ("light level", "brightness", "lux", "illuminance")):
            return "report_illuminance"
        if any(term in lowered for term in ("turn on", "switch on", "light on")):
            return "turn_light_on"
        if any(term in lowered for term in ("turn off", "switch off", "light off")):
            return "turn_light_off"
        return "none"

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

    def _find_relay_entity(
        self,
        *,
        context: AssistantContext,
        lowered_message: str,
        target_hint: str | None,
    ) -> Entity | None:
        writable_relays = [
            entity
            for entity in context.entities
            if entity.writable == 1 and entity.kind == "switch.relay"
        ]
        if not writable_relays:
            return None

        candidates = [lowered_message]
        if target_hint:
            candidates.append(target_hint.lower())

        for entity in writable_relays:
            for candidate in candidates:
                if entity.name.lower() in candidate:
                    return entity
                if entity.capability_id.lower() in candidate:
                    return entity
        return writable_relays[0]
