from __future__ import annotations

from collections.abc import AsyncIterator
import json
from dataclasses import dataclass
from typing import Any

import httpx

from assistant_runtime.core.config import Settings
from assistant_runtime.models import Device, Entity, EntityState, SessionMessage


@dataclass
class PlannerDecision:
    action: str
    reply: str | None = None
    target_hint: str | None = None
    params: dict[str, Any] | None = None


class OllamaPlanner:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def health(self) -> tuple[bool, str]:
        if not self.settings.ollama_model:
            return False, "OLLAMA_MODEL is not configured."

        async with httpx.AsyncClient(timeout=min(self.settings.ollama_timeout_seconds, 5.0)) as client:
            response = await client.get(f"{self.settings.ollama_base_url}/api/tags")
        response.raise_for_status()
        models = response.json().get("models", [])
        names = {item.get("name") for item in models}
        if self.settings.ollama_model not in names:
            return False, f"Model {self.settings.ollama_model} is not pulled in Ollama."
        return True, f"Ollama reachable with model {self.settings.ollama_model}."

    async def plan(
        self,
        *,
        message: str,
        recent_messages: list[SessionMessage],
        devices: list[Device],
        entities: list[Entity],
        states: list[EntityState],
    ) -> PlannerDecision:
        if not self.settings.ollama_model:
            raise RuntimeError("OLLAMA_MODEL is not configured.")

        prompt = self._build_prompt(
            message=message,
            recent_messages=recent_messages,
            devices=devices,
            entities=entities,
            states=states,
        )

        async with httpx.AsyncClient(timeout=self.settings.ollama_timeout_seconds) as client:
            response = await client.post(
                f"{self.settings.ollama_base_url}/api/generate",
                json={
                    "model": self.settings.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
            )
        response.raise_for_status()
        payload = self._extract_json_payload(response.json())
        action = str(payload.get("action", "none")).strip().lower()
        reply = payload.get("reply")
        target_hint = payload.get("target_hint")
        params = payload.get("params") if isinstance(payload.get("params"), dict) else None
        return PlannerDecision(action=action, reply=reply, target_hint=target_hint, params=params)

    async def chat(
        self,
        *,
        recent_messages: list[SessionMessage],
        devices: list[Device],
        entities: list[Entity],
        states: list[EntityState],
    ) -> str:
        if not self.settings.ollama_model:
            raise RuntimeError("OLLAMA_MODEL is not configured.")

        messages = self._build_chat_messages(
            recent_messages=recent_messages,
            devices=devices,
            entities=entities,
            states=states,
        )

        async with httpx.AsyncClient(timeout=self.settings.ollama_timeout_seconds) as client:
            response = await client.post(
                f"{self.settings.ollama_base_url}/api/chat",
                json={
                    "model": self.settings.ollama_model,
                    "messages": messages,
                    "stream": False,
                },
            )
        response.raise_for_status()
        payload = response.json()
        message = payload.get("message")
        if not isinstance(message, dict):
            raise ValueError("Ollama chat response did not include a message payload.")
        content = str(message.get("content", "")).strip()
        if not content:
            raise ValueError("Ollama chat response was empty.")
        return content

    async def stream_chat(
        self,
        *,
        recent_messages: list[SessionMessage],
        devices: list[Device],
        entities: list[Entity],
        states: list[EntityState],
    ) -> AsyncIterator[str]:
        if not self.settings.ollama_model:
            raise RuntimeError("OLLAMA_MODEL is not configured.")

        messages = self._build_chat_messages(
            recent_messages=recent_messages,
            devices=devices,
            entities=entities,
            states=states,
        )

        saw_content = False
        async with httpx.AsyncClient(timeout=self.settings.ollama_timeout_seconds) as client:
            async with client.stream(
                "POST",
                f"{self.settings.ollama_base_url}/api/chat",
                json={
                    "model": self.settings.ollama_model,
                    "messages": messages,
                    "stream": True,
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    payload = json.loads(line)
                    message = payload.get("message")
                    if not isinstance(message, dict):
                        continue
                    content = str(message.get("content", ""))
                    if not content:
                        continue
                    saw_content = True
                    yield content

        if not saw_content:
            raise ValueError("Ollama chat stream returned no content.")

    def _build_prompt(
        self,
        *,
        message: str,
        recent_messages: list[SessionMessage],
        devices: list[Device],
        entities: list[Entity],
        states: list[EntityState],
    ) -> str:
        state_map = {item.entity_id: item for item in states}
        entity_lines = []
        for entity in entities:
            state = state_map.get(entity.id)
            rendered_state = state.value if state is not None else {}
            entity_lines.append(
                f"- {entity.name} | id={entity.id} | kind={entity.kind} | writable={entity.writable} | state={rendered_state}"
            )

        device_lines = [
            f"- {device.name} | id={device.id} | type={device.device_type} | status={device.status}"
            for device in devices
        ]

        history_lines = [
            f"{item.role.upper()}: {item.content}"
            for item in recent_messages[-8:]
        ]

        return f"""
You are Alice Assistant Runtime. You do not control devices directly. You can only choose one Home OS tool action.

Allowed actions:
- none
- stack_health
- show_device_detail
- show_auto_light_status
- enable_auto_light
- disable_auto_light
- update_auto_light_thresholds
- update_auto_light_mapping
- list_recent_audit_events
- list_online_devices
- report_temperature
- report_illuminance
- turn_light_on
- turn_light_off

Rules:
- Return JSON only.
- Do not invent devices or state.
- If the user refers to an earlier device indirectly, use target_hint to name it.
- If unsure, use action "none".
- Only use params for numeric settings changes.
- Allowed params keys for settings edits: on_raw, off_raw, on_lux, off_lux, sensor_entity_id, target_entity_id.
- Keep reply concise and factual.

Conversation history:
{chr(10).join(history_lines) if history_lines else "- none"}

Known devices:
{chr(10).join(device_lines) if device_lines else "- none"}

Known entities:
{chr(10).join(entity_lines) if entity_lines else "- none"}

Current user message:
{message}

Return exactly one JSON object with this shape:
{{
  "action": "one allowed action string",
  "reply": "short reply for the user",
  "target_hint": "optional device/entity name if relevant",
  "params": {{
    "on_raw": 3000,
    "off_raw": 2600,
    "on_lux": 50,
    "off_lux": 35,
    "sensor_entity_id": "ent_dev_sensor_hall_01_illuminance",
    "target_entity_id": "ent_dev_light_bench_01_relay"
  }}
}}
""".strip()

    def _build_chat_messages(
        self,
        *,
        recent_messages: list[SessionMessage],
        devices: list[Device],
        entities: list[Entity],
        states: list[EntityState],
    ) -> list[dict[str, str]]:
        online_devices = [device.name for device in devices if device.status == "online"]
        temperature_entities = [
            entity.name
            for entity in entities
            if entity.kind == "sensor.temperature"
        ]
        illuminance_entities = [
            entity.name
            for entity in entities
            if entity.kind == "sensor.illuminance"
        ]
        writable_relays = [
            entity.name
            for entity in entities
            if entity.kind == "switch.relay" and entity.writable == 1
        ]
        latest_states = []
        state_map = {item.entity_id: item for item in states}
        for entity in entities[:8]:
            state = state_map.get(entity.id)
            if state is None:
                continue
            latest_states.append(f"{entity.name}={state.value}")

        system_prompt = f"""
You are Alice, the conversational assistant for a local smart-home stack called Alice Home OS.

Style:
- Talk like a normal modern chat assistant.
- Be warm, natural, and concise.
- For simple greetings or chit-chat, reply like a real assistant instead of listing capabilities.
- Keep replies short unless the user asks for more detail.
- Use plain ASCII punctuation only.
- Do not use emoji.
- Do not roleplay, gush, or sound theatrical.
- Keep the tone calm and grounded, closer to ChatGPT than a character bot.

Safety and tool boundaries:
- Do not claim you changed devices, automations, or settings unless a real tool action already happened in this session.
- If the user asks for smart-home actions or live house facts, the app may route those through tools separately. In plain chat mode, do not invent live results.
- You can still discuss what you can help with in a natural way.

Current house context:
- Online devices: {", ".join(online_devices) if online_devices else "none"}
- Writable relays: {", ".join(writable_relays) if writable_relays else "none"}
- Temperature sensors: {", ".join(temperature_entities) if temperature_entities else "none"}
- Light sensors: {", ".join(illuminance_entities) if illuminance_entities else "none"}
- Recent known state snippets: {"; ".join(latest_states) if latest_states else "none"}
""".strip()

        messages = [{"role": "system", "content": system_prompt}]
        for item in recent_messages[-10:]:
            if item.role not in {"user", "assistant"}:
                continue
            messages.append({"role": item.role, "content": item.content})
        return messages

    def _extract_json_payload(self, raw_response: dict) -> dict:
        candidates = [
            raw_response.get("response"),
            raw_response.get("thinking"),
        ]
        for candidate in candidates:
            if not candidate:
                continue
            parsed = self._parse_candidate(candidate)
            if parsed is not None:
                return parsed
        raise ValueError("Ollama did not return a parseable JSON planner payload.")

    def _parse_candidate(self, text: str) -> dict | None:
        stripped = text.strip()
        if not stripped:
            return None

        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None

        fragment = stripped[start : end + 1]
        try:
            parsed = json.loads(fragment)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return None
        return None
