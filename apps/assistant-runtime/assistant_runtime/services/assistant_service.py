from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Protocol

from assistant_runtime.clients.home_os_gateway import HomeOsGateway
from assistant_runtime.core.config import Settings
from assistant_runtime.models import Device, DeviceDetailEntity, Entity, EntityState, SessionMessage
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

    async def chat(
        self,
        *,
        recent_messages: list[SessionMessage],
        devices: list[Device],
        entities: list[Entity],
        states: list[EntityState],
    ) -> str: ...


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
        deterministic_action = self._infer_deterministic_action(lowered)
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
        planner_params: dict[str, Any] | None = None
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
                planner_params = decision.params
            except Exception as exc:
                if self.settings.assistant_mode == "ollama" and not self.settings.assistant_allow_fallback:
                    raise
                fallback_used = True
                planner_error = str(exc)
                traces.append(ToolTrace(tool="planner.ollama", status="fallback", detail=str(exc)))

        if planner_action and planner_action != "none":
            response = await self._execute_action(
                action=planner_action,
                lowered_message=lowered,
                traces=traces,
                mode=mode,
                context=context,
                planner_reply=planner_reply,
                planner_target_hint=planner_target_hint,
                planner_params=planner_params,
            )
        elif (
            self.settings.assistant_mode in {"auto", "ollama"}
            and deterministic_action == "none"
            and (planner_source == "ollama" or planner_error is not None)
        ):
            try:
                response = await self._respond_with_conversation(
                    traces=traces,
                    context=context,
                    recent_messages=recent_messages,
                    planner_error=planner_error,
                )
            except Exception as exc:
                fallback_used = True
                traces.append(ToolTrace(tool="chat.ollama", status="fallback", detail=str(exc)))
                response = await self._execute_action(
                    action=deterministic_action,
                    lowered_message=lowered,
                    traces=traces,
                    mode="deterministic",
                    context=context,
                    planner_reply=None,
                    planner_target_hint=None,
                    planner_params=None,
                )
        else:
            response = await self._execute_action(
                action=deterministic_action,
                lowered_message=lowered,
                traces=traces,
                mode="deterministic",
                context=context,
                planner_reply=None,
                planner_target_hint=None,
                planner_params=None,
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

    async def _respond_with_conversation(
        self,
        *,
        traces: list[ToolTrace],
        context: AssistantContext | None,
        recent_messages: list[SessionMessage],
        planner_error: str | None,
    ) -> ChatResponse:
        context = context or await self._load_context(traces)
        reply = await self.planner.chat(
            recent_messages=recent_messages,
            devices=context.devices,
            entities=context.entities,
            states=context.states,
        )
        traces.append(ToolTrace(tool="chat.ollama", status="ok", detail="Generated conversational reply"))
        return ChatResponse(
            session_id="",
            mode="ollama",
            success=True,
            reply=reply,
            tool_traces=traces,
            debug=self._build_debug(
                response_mode="ollama",
                planner_source="ollama",
                fallback_used=planner_error is not None,
                planner_error=planner_error,
            ),
        )

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
        planner_params: dict[str, Any] | None,
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

        if action == "show_device_detail":
            target = self._find_device(
                context=context,
                lowered_message=lowered_message,
                target_hint=planner_target_hint,
            )
            if target is None:
                return ChatResponse(
                    session_id="",
                    mode=mode,
                    success=False,
                    reply="I could not determine which device you want details for. Try naming the device explicitly.",
                    tool_traces=traces,
                    debug=self._build_debug(
                        response_mode=mode,
                        planner_source=("ollama" if mode == "ollama" else "deterministic"),
                        fallback_used=False,
                        planner_error=None,
                    ),
                )
            detail = await self.gateway.get_device_detail(device_id=target.id)
            traces.append(ToolTrace(tool="devices.detail", status="ok", detail=f"Loaded detail for {detail.device.name}"))
            entity_parts = [self._format_device_entity_summary(entity) for entity in detail.entities[:5]]
            audit_parts = [f"{event.action} at {event.created_at}" for event in detail.audit_events[:3]]
            reply = planner_reply or (
                f"{detail.device.name} is {detail.device.status} "
                f"({detail.device.device_type}, fw {detail.device.fw_version or 'unknown'}). "
                f"Entities: {'; '.join(entity_parts) if entity_parts else 'none'}. "
                f"Recent activity: {'; '.join(audit_parts) if audit_parts else 'none'}."
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

        if action == "show_auto_light_status":
            settings = await self.gateway.get_auto_light_settings()
            traces.append(ToolTrace(tool="system.auto_light.get", status="ok", detail="Fetched auto-light settings"))
            status = "enabled" if settings.enabled else "disabled"
            reply = planner_reply or (
                f"Auto-light is {status}. "
                f"Mode: {settings.mode}. "
                f"Sensor: {settings.sensor_entity_id or 'not set'}. "
                f"Target: {settings.target_entity_id or 'not set'}. "
                f"Thresholds: on raw {settings.on_raw}, off raw {settings.off_raw}, on lux {settings.on_lux}, off lux {settings.off_lux}."
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

        if action in {"enable_auto_light", "disable_auto_light"}:
            enabled = action == "enable_auto_light"
            settings = await self.gateway.update_auto_light_enabled(enabled=enabled)
            traces.append(
                ToolTrace(
                    tool="system.auto_light.put",
                    status="ok",
                    detail=f"{'Enabled' if enabled else 'Disabled'} auto-light",
                )
            )
            reply = planner_reply or (
                f"Auto-light is now {'enabled' if settings.enabled else 'disabled'}. "
                f"Mode: {settings.mode}. "
                f"Target: {settings.target_entity_id or 'not set'}."
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

        if action == "update_auto_light_thresholds":
            changes = planner_params or self._extract_auto_light_threshold_changes(lowered_message)
            if not changes:
                return ChatResponse(
                    session_id="",
                    mode=mode,
                    success=False,
                    reply="I could not determine which auto-light thresholds to change. Try specifying on/off and raw/lux values.",
                    tool_traces=traces,
                    debug=self._build_debug(
                        response_mode=mode,
                        planner_source=("ollama" if mode == "ollama" else "deterministic"),
                        fallback_used=False,
                        planner_error=None,
                    ),
                )
            settings = await self.gateway.update_auto_light_settings(**changes)
            traces.append(
                ToolTrace(
                    tool="system.auto_light.put",
                    status="ok",
                    detail="Updated auto-light thresholds",
                )
            )
            reply = planner_reply or (
                "Updated auto-light thresholds. "
                f"On raw: {settings.on_raw}, off raw: {settings.off_raw}, "
                f"on lux: {settings.on_lux}, off lux: {settings.off_lux}."
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

        if action == "update_auto_light_mapping":
            changes = planner_params or self._extract_auto_light_mapping_changes(lowered_message, context)
            if not changes:
                return ChatResponse(
                    session_id="",
                    mode=mode,
                    success=False,
                    reply="I could not determine which auto-light sensor or target to change. Try naming the sensor or light explicitly.",
                    tool_traces=traces,
                    debug=self._build_debug(
                        response_mode=mode,
                        planner_source=("ollama" if mode == "ollama" else "deterministic"),
                        fallback_used=False,
                        planner_error=None,
                    ),
                )
            settings = await self.gateway.update_auto_light_settings(**changes)
            traces.append(
                ToolTrace(
                    tool="system.auto_light.put",
                    status="ok",
                    detail="Updated auto-light mapping",
                )
            )
            reply = planner_reply or (
                "Updated auto-light mapping. "
                f"Sensor: {self._describe_entity(context, settings.sensor_entity_id) or 'not set'}. "
                f"Target: {self._describe_entity(context, settings.target_entity_id) or 'not set'}."
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

        if action == "list_recent_audit_events":
            events = await self.gateway.list_audit_events(limit=5)
            traces.append(ToolTrace(tool="audit.list", status="ok", detail=f"Loaded {len(events)} audit events"))
            if not events:
                reply = planner_reply or "There are no recent audit events."
            else:
                parts = [
                    f"{event.action} on {event.target_id or event.target_type} at {event.created_at}"
                    for event in events[:5]
                ]
                reply = planner_reply or ("Recent audit events: " + "; ".join(parts) + ".")
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
                "I can currently show stack health, list online devices, show device details, report temperature or light readings, "
                "turn the light relay on or off, show or toggle auto-light, edit auto-light thresholds or mappings, "
                "and list recent audit events."
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
        normalized = lowered.replace("-", " ")
        if any(phrase in lowered for phrase in ("stack health", "system health", "hub health")):
            return "stack_health"
        if any(
            phrase in normalized
            for phrase in ("device details", "device detail", "details", "detail", "what's going on with", "what is going on with", "details for", "tell me about")
        ):
            return "show_device_detail"
        if "auto light" in normalized or "automatic light" in normalized:
            if self._looks_like_auto_light_mapping_update(normalized):
                return "update_auto_light_mapping"
            if self._extract_auto_light_threshold_changes(normalized):
                return "update_auto_light_thresholds"
            if any(
                phrase in normalized
                for phrase in (
                    "is auto light",
                    "is automatic light",
                    "auto light status",
                    "auto light settings",
                    "auto light enabled",
                    "auto light disabled",
                )
            ):
                return "show_auto_light_status"
            if any(term in normalized for term in ("turn on", "switch on", "enable")):
                return "enable_auto_light"
            if any(term in normalized for term in ("turn off", "switch off", "disable")):
                return "disable_auto_light"
            return "show_auto_light_status"
        if any(
            phrase in normalized
            for phrase in ("recent events", "recent activity", "latest events", "event log", "activity log", "audit")
        ) or normalized.startswith("what happened"):
            return "list_recent_audit_events"
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

    def _extract_auto_light_threshold_changes(self, lowered: str) -> dict[str, float]:
        normalized = lowered.replace("-", " ")
        if "auto light" not in normalized and "automatic light" not in normalized:
            return {}

        changes: dict[str, float] = {}
        patterns = {
            "on_raw": [
                r"\bon raw\b[^0-9-]*(-?\d+(?:\.\d+)?)",
                r"\braw on\b[^0-9-]*(-?\d+(?:\.\d+)?)",
            ],
            "off_raw": [
                r"\boff raw\b[^0-9-]*(-?\d+(?:\.\d+)?)",
                r"\braw off\b[^0-9-]*(-?\d+(?:\.\d+)?)",
            ],
            "on_lux": [
                r"\bon lux\b[^0-9-]*(-?\d+(?:\.\d+)?)",
                r"\blux on\b[^0-9-]*(-?\d+(?:\.\d+)?)",
            ],
            "off_lux": [
                r"\boff lux\b[^0-9-]*(-?\d+(?:\.\d+)?)",
                r"\blux off\b[^0-9-]*(-?\d+(?:\.\d+)?)",
            ],
        }
        for key, key_patterns in patterns.items():
            value = self._find_first_float(normalized, key_patterns)
            if value is not None:
                changes[key] = value
        return changes

    def _find_first_float(self, text: str, patterns: list[str]) -> float | None:
        for pattern in patterns:
            match = re.search(pattern, text)
            if match is None:
                continue
            try:
                return float(match.group(1))
            except ValueError:
                continue
        return None

    def _looks_like_auto_light_mapping_update(self, lowered: str) -> bool:
        hints = self._extract_auto_light_mapping_hints(lowered)
        return bool(hints)

    def _extract_auto_light_mapping_changes(self, lowered: str, context: AssistantContext) -> dict[str, str]:
        hints = self._extract_auto_light_mapping_hints(lowered)
        changes: dict[str, str] = {}

        sensor_hint = hints.get("sensor")
        if sensor_hint:
            sensor = self._resolve_auto_light_sensor(context, sensor_hint)
            if sensor is not None:
                changes["sensor_entity_id"] = sensor.id

        target_hint = hints.get("target")
        if target_hint:
            target = self._resolve_auto_light_target(context, target_hint)
            if target is not None:
                changes["target_entity_id"] = target.id

        return changes

    def _extract_auto_light_mapping_hints(self, lowered: str) -> dict[str, str]:
        normalized = lowered.replace("-", " ")
        if "auto light" not in normalized and "automatic light" not in normalized:
            return {}

        hints: dict[str, str] = {}
        sensor_patterns = [
            r"\bsensor to ([a-z0-9 _]+?)(?:\s+and\s+target\b|$)",
            r"\bsensor as ([a-z0-9 _]+?)(?:\s+and\s+target\b|$)",
            r"\buse ([a-z0-9 _]+?) as (?:the )?auto light sensor\b",
        ]
        target_patterns = [
            r"\btarget to ([a-z0-9 _]+?)(?:\s+and\s+sensor\b|$)",
            r"\btarget as ([a-z0-9 _]+?)(?:\s+and\s+sensor\b|$)",
            r"\buse ([a-z0-9 _]+?) as (?:the )?auto light target\b",
        ]

        sensor_hint = self._find_first_hint(normalized, sensor_patterns)
        if sensor_hint:
            hints["sensor"] = sensor_hint

        target_hint = self._find_first_hint(normalized, target_patterns)
        if target_hint:
            hints["target"] = target_hint

        return hints

    def _find_first_hint(self, text: str, patterns: list[str]) -> str | None:
        for pattern in patterns:
            match = re.search(pattern, text)
            if match is None:
                continue
            hint = self._clean_mapping_hint(match.group(1))
            if hint:
                return hint
        return None

    def _clean_mapping_hint(self, hint: str) -> str:
        cleaned = " ".join(hint.strip().split())
        for prefix in ("the ", "a ", "an "):
            if cleaned.startswith(prefix):
                return cleaned[len(prefix) :]
        return cleaned

    def _resolve_auto_light_sensor(self, context: AssistantContext, hint: str) -> Entity | None:
        candidates = [entity for entity in context.entities if entity.kind == "sensor.illuminance"]
        return self._resolve_entity_hint(candidates, hint)

    def _resolve_auto_light_target(self, context: AssistantContext, hint: str) -> Entity | None:
        candidates = [
            entity
            for entity in context.entities
            if entity.kind == "switch.relay" and entity.writable == 1
        ]
        return self._resolve_entity_hint(candidates, hint)

    def _resolve_entity_hint(self, entities: list[Entity], hint: str) -> Entity | None:
        normalized_hint = hint.lower()
        for entity in entities:
            if entity.name.lower() == normalized_hint or entity.id.lower() == normalized_hint:
                return entity
        for entity in entities:
            if normalized_hint in entity.name.lower():
                return entity
            if normalized_hint in entity.id.lower():
                return entity
            if normalized_hint in entity.capability_id.lower():
                return entity
        return None

    def _describe_entity(self, context: AssistantContext, entity_id: str | None) -> str | None:
        if entity_id is None:
            return None
        for entity in context.entities:
            if entity.id == entity_id:
                return entity.name
        return entity_id

    def _find_device(
        self,
        *,
        context: AssistantContext,
        lowered_message: str,
        target_hint: str | None,
    ) -> Device | None:
        candidates = [lowered_message]
        if target_hint:
            candidates.append(target_hint.lower())

        for device in context.devices:
            for candidate in candidates:
                if device.name.lower() in candidate:
                    return device
                if device.id.lower() in candidate:
                    return device
        return None

    def _format_device_entity_summary(self, entity: DeviceDetailEntity) -> str:
        if entity.state is None:
            return f"{entity.name}: no state"
        state_pairs = ", ".join(f"{key}={value}" for key, value in entity.state.items())
        return f"{entity.name}: {state_pairs}"

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
