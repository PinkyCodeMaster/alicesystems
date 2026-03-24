from __future__ import annotations

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
