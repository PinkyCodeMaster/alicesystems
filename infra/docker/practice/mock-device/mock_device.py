from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import math
import os
from pathlib import Path
import threading
import time
from typing import Any
from urllib import error, request

import paho.mqtt.client as mqtt


logging.basicConfig(
    level=os.getenv("MOCK_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("alice.mock-device")


def _env(name: str, default: str) -> str:
    return os.getenv(name, default).strip()


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return int(raw)


def _json_dump(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True).encode("utf-8")


def _normalize_base_url(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("Hub API base URL is required.")
    if not normalized.startswith(("http://", "https://")):
        normalized = f"http://{normalized}"
    return normalized.rstrip("/")


class MockDevice:
    def __init__(self) -> None:
        self.device_kind = _env("MOCK_DEVICE_KIND", "sensor")
        self.bootstrap_id = _env("MOCK_BOOTSTRAP_ID", "boot_mock_sensor_01")
        self.device_id = _env("MOCK_DEVICE_ID", "dev_mock_sensor_01")
        self.device_name = _env("MOCK_DEVICE_NAME", "Practice Mock Device")
        self.model = _env("MOCK_MODEL", "alice.sensor.env.s1")
        self.device_type = _env("MOCK_DEVICE_TYPE", "sensor_node")
        self.protocol = _env("MOCK_PROTOCOL", "wifi-mqtt")
        self.fw_version = _env("MOCK_FW_VERSION", "0.2.0-practice")
        self.setup_ap_ssid = _env("MOCK_SETUP_AP_SSID", f"AliceSetup-{self.device_id}")
        self.setup_ap_password = _env("MOCK_SETUP_AP_PASSWORD", "alice-setup")
        self.default_hub_api_base_url = _normalize_base_url(
            _env("MOCK_HUB_API_BASE_URL", "http://hub-api:8000/api/v1")
        )
        self.default_mqtt_host = _env("MOCK_MQTT_HOST", "mosquitto")
        self.default_mqtt_port = _env_int("MOCK_MQTT_PORT", 1883)
        self.default_mqtt_topic_prefix = _env("MOCK_MQTT_TOPIC_PREFIX", "alice/v1")
        self.mqtt_client_id = _env("MOCK_MQTT_CLIENT_ID", self.device_id)
        self.setup_port = _env_int("MOCK_SETUP_PORT", 8080)
        self.state_file = Path(_env("MOCK_STATE_FILE", "/data/mock-device-state.json"))
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._mqtt_connected = False
        self._mqtt_client: mqtt.Client | None = None
        self._mqtt_started = False
        self._last_sensor_publish = 0.0
        self._last_relay_publish = 0.0
        self._relay_on = False
        self._runtime: dict[str, Any] = self._load_runtime_state()
        self.device_id = self._runtime.get("device_id", self.device_id)
        self.mqtt_client_id = self._runtime.get("mqtt_client_id", self.mqtt_client_id)
        self.device_name = self._runtime.get("device_name", self.device_name)

        if self._runtime.get("claimed"):
            self._restart_mqtt_client()

    def _load_runtime_state(self) -> dict[str, Any]:
        if not self.state_file.exists():
            return {"claimed": False}
        try:
            return json.loads(self.state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.warning("Failed to load runtime state from %s, starting unclaimed.", self.state_file)
            return {"claimed": False}

    def _save_runtime_state(self) -> None:
        self.state_file.write_text(json.dumps(self._runtime, indent=2, sort_keys=True), encoding="utf-8")

    def _mqtt_host(self) -> str:
        return self._runtime.get("mqtt_host") or self.default_mqtt_host

    def _mqtt_port(self) -> int:
        return int(self._runtime.get("mqtt_port") or self.default_mqtt_port)

    def _mqtt_topic_prefix(self) -> str:
        return self._runtime.get("mqtt_topic_prefix") or self.default_mqtt_topic_prefix

    def _mqtt_username(self) -> str | None:
        return self._runtime.get("mqtt_username")

    def _mqtt_password(self) -> str | None:
        return self._runtime.get("mqtt_password")

    def _hub_api_candidates(self, requested_base_url: str | None) -> list[str]:
        candidates: list[str] = []
        if requested_base_url:
            candidates.append(_normalize_base_url(requested_base_url))
        if self.default_hub_api_base_url not in candidates:
            candidates.append(self.default_hub_api_base_url)
        return candidates

    def status_payload(self) -> dict[str, Any]:
        with self._lock:
            return {
                "device_kind": self.device_kind,
                "bootstrap_id": self.bootstrap_id,
                "device_id": self.device_id,
                "device_name": self._runtime.get("device_name", self.device_name),
                "claimed": bool(self._runtime.get("claimed")),
                "setup_ap_ssid": self.setup_ap_ssid,
                "setup_ap_password": self.setup_ap_password,
                "mqtt_connected": self._mqtt_connected,
                "hub_api_base_url": self._runtime.get("hub_api_base_url", self.default_hub_api_base_url),
                "mqtt_host": self._mqtt_host(),
                "mqtt_port": self._mqtt_port(),
                "mqtt_topic_prefix": self._mqtt_topic_prefix(),
            }

    def handle_provision(self, payload: dict[str, Any]) -> dict[str, Any]:
        bootstrap_id = str(payload.get("bootstrap_id") or "").strip()
        claim_token = str(payload.get("claim_token") or "").strip()
        if bootstrap_id != self.bootstrap_id:
            raise ValueError(f"Bootstrap mismatch. Expected {self.bootstrap_id}.")
        if not claim_token:
            raise ValueError("claim_token is required.")

        wifi_ssid = str(payload.get("wifi_ssid") or "").strip() or None
        wifi_password = payload.get("wifi_password")
        requested_hub_api_base_url = payload.get("hub_api_base_url")
        last_error: Exception | None = None
        response_payload: dict[str, Any] | None = None
        selected_hub_api_base_url: str | None = None

        for hub_api_base_url in self._hub_api_candidates(
            str(requested_hub_api_base_url).strip() if requested_hub_api_base_url else None
        ):
            try:
                response_payload = self._complete_claim(hub_api_base_url, claim_token)
                selected_hub_api_base_url = hub_api_base_url
                break
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning("Claim attempt against %s failed: %s", hub_api_base_url, exc)

        if response_payload is None or selected_hub_api_base_url is None:
            assert last_error is not None
            raise ValueError(str(last_error)) from last_error

        with self._lock:
            self.device_id = response_payload["device_id"]
            self.mqtt_client_id = response_payload["mqtt_client_id"]
            self.device_name = response_payload["device_name"]
            self._runtime = {
                "claimed": True,
                "bootstrap_id": self.bootstrap_id,
                "device_id": self.device_id,
                "device_name": self.device_name,
                "hub_api_base_url": selected_hub_api_base_url,
                "mqtt_host": response_payload["mqtt_host"],
                "mqtt_port": response_payload["mqtt_port"],
                "mqtt_topic_prefix": response_payload["mqtt_topic_prefix"],
                "mqtt_username": response_payload["mqtt_username"],
                "mqtt_password": response_payload["mqtt_password"],
                "mqtt_client_id": self.mqtt_client_id,
                "wifi_ssid": wifi_ssid,
                "wifi_password": wifi_password,
                "claimed_at": time.time(),
            }
            self._save_runtime_state()
        self._restart_mqtt_client()

        return {
            "accepted": True,
            "restart_scheduled": True,
            "bootstrap_id": self.bootstrap_id,
            "setup_ap_ssid": self.setup_ap_ssid,
            "detail": f"Provisioning accepted for {response_payload['device_id']}.",
        }

    def _complete_claim(self, hub_api_base_url: str, claim_token: str) -> dict[str, Any]:
        claim_url = f"{hub_api_base_url}/provisioning/claim/complete"
        body = {
            "bootstrap_id": self.bootstrap_id,
            "claim_token": claim_token,
            "fw_version": self.fw_version,
            "protocol": self.protocol,
            "mqtt_client_id": self.mqtt_client_id,
        }
        response = self._post_json(claim_url, body)
        if "device_id" not in response:
            raise ValueError(f"Unexpected claim response from {claim_url}.")
        return response

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        req = request.Request(
            url,
            data=_json_dump(payload),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ValueError(f"{exc.code} {exc.reason}: {detail}") from exc
        except error.URLError as exc:
            raise ValueError(f"Unable to reach {url}: {exc.reason}") from exc

    def _restart_mqtt_client(self) -> None:
        with self._lock:
            if self._mqtt_client is not None:
                try:
                    if self._mqtt_connected:
                        self._publish_availability("offline")
                    self._mqtt_client.disconnect()
                except Exception:  # noqa: BLE001
                    pass
                if self._mqtt_started:
                    self._mqtt_client.loop_stop()
                self._mqtt_client = None
                self._mqtt_started = False
                self._mqtt_connected = False

            client_id = self._runtime.get("mqtt_client_id") or self.mqtt_client_id
            client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id=client_id,
            )
            username = self._mqtt_username()
            password = self._mqtt_password()
            if username:
                client.username_pw_set(username, password or None)
            client.on_connect = self._on_mqtt_connect
            client.on_disconnect = self._on_mqtt_disconnect
            client.on_message = self._on_mqtt_message
            client.reconnect_delay_set(min_delay=1, max_delay=10)
            client.connect_async(self._mqtt_host(), self._mqtt_port(), keepalive=60)
            client.loop_start()
            self._mqtt_client = client
            self._mqtt_started = True
            logger.info(
                "Starting MQTT loop for %s against %s:%s",
                self.device_id,
                self._mqtt_host(),
                self._mqtt_port(),
            )

    def _on_mqtt_connect(self, client: mqtt.Client, _userdata, _flags, reason_code, _properties) -> None:
        with self._lock:
            self._mqtt_connected = True
        logger.info("MQTT connected for %s with reason %s", self.device_id, reason_code)
        if self.device_kind == "relay":
            client.subscribe(self._topic("cmd"))
        self._publish_hello()
        self._publish_availability("online")
        if self.device_kind == "relay":
            self._publish_relay_state()

    def _on_mqtt_disconnect(self, _client: mqtt.Client, _userdata, _flags, reason_code, _properties) -> None:
        with self._lock:
            self._mqtt_connected = False
        logger.info("MQTT disconnected for %s with reason %s", self.device_id, reason_code)

    def _on_mqtt_message(self, _client: mqtt.Client, _userdata, message: mqtt.MQTTMessage) -> None:
        if self.device_kind != "relay":
            return
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except json.JSONDecodeError:
            logger.warning("Ignoring malformed command payload on %s", message.topic)
            return

        params = payload.get("params") or {}
        next_state = bool(params.get("on"))
        with self._lock:
            self._relay_on = next_state
        self._publish_relay_state()
        ack_payload = {
            "cmd_id": payload.get("cmd_id"),
            "target_entity_id": payload.get("target_entity_id"),
            "status": "applied",
            "name": payload.get("name", "switch.set"),
            "params": {"on": next_state},
            "state": {"on": next_state},
        }
        self._publish_json(self._topic("ack"), ack_payload)

    def _topic(self, message_type: str) -> str:
        return f"{self._mqtt_topic_prefix()}/device/{self.device_id}/{message_type}"

    def _capabilities(self) -> list[dict[str, Any]]:
        if self.device_kind == "relay":
            return [
                {
                    "capability_id": "relay",
                    "kind": "switch.relay",
                    "name": "Relay",
                    "slug": "relay",
                    "writable": 1,
                    "traits": {},
                }
            ]
        return [
            {
                "capability_id": "temperature",
                "kind": "sensor.temperature",
                "name": "Temperature",
                "slug": "temperature",
                "writable": 0,
                "traits": {"unit": "C"},
            },
            {
                "capability_id": "motion",
                "kind": "sensor.motion",
                "name": "Motion",
                "slug": "motion",
                "writable": 0,
                "traits": {},
            },
            {
                "capability_id": "illuminance",
                "kind": "sensor.illuminance",
                "name": "Illuminance",
                "slug": "illuminance",
                "writable": 0,
                "traits": {"unit": "lux"},
            },
        ]

    def _publish_json(self, topic: str, payload: dict[str, Any], retain: bool = False) -> None:
        with self._lock:
            client = self._mqtt_client
        if client is None:
            return
        result = client.publish(topic, _json_dump(payload), qos=0, retain=retain)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            logger.warning("Publish failed to %s with rc=%s", topic, result.rc)

    def _publish_hello(self) -> None:
        payload = {
            "name": self._runtime.get("device_name", self.device_name),
            "model": self.model,
            "device_type": self.device_type,
            "protocol": self.protocol,
            "fw_version": self.fw_version,
            "mqtt_client_id": self._runtime.get("mqtt_client_id", self.mqtt_client_id),
            "capabilities": self._capabilities(),
        }
        self._publish_json(self._topic("hello"), payload, retain=True)

    def _publish_availability(self, status: str) -> None:
        self._publish_json(self._topic("availability"), {"status": status}, retain=True)

    def _publish_relay_state(self) -> None:
        self._publish_json(self._topic("state"), {"capability": "relay", "on": self._relay_on})

    def _publish_sensor_state(self) -> None:
        now = time.time()
        phase = now / 30.0
        temperature = round(20.8 + math.sin(phase) * 1.3, 1)
        lux = round(55 + math.sin(phase / 2.0) * 20, 1)
        raw = int(3400 - lux * 10)
        motion = int(now / 20) % 2 == 0
        self._publish_json(self._topic("state"), {"capability": "temperature", "celsius": temperature})
        self._publish_json(self._topic("state"), {"capability": "illuminance", "lux": lux, "raw": raw})
        self._publish_json(self._topic("state"), {"capability": "motion", "motion": motion})

    def run(self) -> None:
        while not self._stop_event.is_set():
            with self._lock:
                claimed = bool(self._runtime.get("claimed"))
                connected = self._mqtt_connected
            now = time.time()
            if claimed and connected and self.device_kind == "sensor" and now - self._last_sensor_publish >= 8:
                self._publish_sensor_state()
                self._last_sensor_publish = now
            if claimed and connected and self.device_kind == "relay" and now - self._last_relay_publish >= 15:
                self._publish_relay_state()
                self._last_relay_publish = now
            time.sleep(1)

    def stop(self) -> None:
        self._stop_event.set()
        with self._lock:
            client = self._mqtt_client
            connected = self._mqtt_connected
        if client is not None:
            try:
                if connected:
                    self._publish_availability("offline")
                client.disconnect()
                if self._mqtt_started:
                    client.loop_stop()
            except Exception:  # noqa: BLE001
                pass


def build_handler(device: MockDevice):
    class DeviceHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path not in {"/", "/health"}:
                self._send_json({"detail": "Not found."}, status=404)
                return
            self._send_json(device.status_payload())

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/provision":
                self._send_json({"detail": "Not found."}, status=404)
                return
            length = int(self.headers.get("Content-Length") or "0")
            raw_body = self.rfile.read(length)
            try:
                payload = json.loads(raw_body.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                self._send_json({"detail": "Invalid JSON."}, status=400)
                return
            try:
                response_payload = device.handle_provision(payload)
            except ValueError as exc:
                self._send_json({"detail": str(exc)}, status=409)
                return
            self._send_json(response_payload, status=200)

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(204)
            self._send_cors_headers()
            self.end_headers()

        def log_message(self, format_: str, *args: Any) -> None:
            logger.info("%s - %s", self.address_string(), format_ % args)

        def _send_cors_headers(self) -> None:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "*")
            self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")

        def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
            body = _json_dump(payload)
            self.send_response(status)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return DeviceHandler


def main() -> None:
    device = MockDevice()
    server = ThreadingHTTPServer(("0.0.0.0", device.setup_port), build_handler(device))
    worker = threading.Thread(target=device.run, daemon=True)
    worker.start()
    logger.info(
        "Mock %s device ready on port %s. Bootstrap ID=%s device ID=%s setup SSID=%s",
        device.device_kind,
        device.setup_port,
        device.bootstrap_id,
        device.device_id,
        device.setup_ap_ssid,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        device.stop()


if __name__ == "__main__":
    main()
