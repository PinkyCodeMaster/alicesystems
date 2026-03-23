from __future__ import annotations

import json
import logging
from threading import Lock

import paho.mqtt.client as mqtt

from app.core.config import Settings
from app.core.db import get_session_factory

logger = logging.getLogger(__name__)

_manager = None
_manager_lock = Lock()


class MqttManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._started = False
        self._connected = False
        self.client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=settings.mqtt_client_id,
        )
        if settings.mqtt_username:
            self.client.username_pw_set(settings.mqtt_username, settings.mqtt_password)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    @property
    def started(self) -> bool:
        return self._started

    @property
    def connected(self) -> bool:
        return self._connected

    def start(self) -> None:
        if not self.settings.mqtt_enabled or self._started:
            return

        self.client.connect_async(self.settings.mqtt_host, self.settings.mqtt_port, keepalive=60)
        self.client.loop_start()
        self._started = True
        logger.info(
            "MQTT manager started for %s:%s",
            self.settings.mqtt_host,
            self.settings.mqtt_port,
            extra={
                "event": {
                    "action": "mqtt.manager_started",
                    "host": self.settings.mqtt_host,
                    "port": self.settings.mqtt_port,
                }
            },
        )

    def stop(self) -> None:
        if not self._started:
            return
        try:
            self.client.disconnect()
        finally:
            self.client.loop_stop()
            self._started = False
            logger.info("MQTT manager stopped", extra={"event": {"action": "mqtt.manager_stopped"}})

    def publish_json(self, topic: str, payload: dict, *, retain: bool = False) -> bool:
        if not self._started or not self._connected:
            return False
        result = self.client.publish(topic, json.dumps(payload), qos=0, retain=retain)
        return result.rc == mqtt.MQTT_ERR_SUCCESS

    def _on_connect(self, client, _userdata, _flags, reason_code, _properties) -> None:
        if reason_code != 0:
            self._connected = False
            logger.warning(
                "MQTT connect failed with reason code %s",
                reason_code,
                extra={"event": {"action": "mqtt.connect_failed", "reason_code": int(reason_code)}},
            )
            return

        self._connected = True
        prefix = self.settings.mqtt_topic_prefix
        topics = [
            f"{prefix}/device/+/hello",
            f"{prefix}/device/+/availability",
            f"{prefix}/device/+/telemetry",
            f"{prefix}/device/+/state",
            f"{prefix}/device/+/ack",
        ]
        for topic in topics:
            client.subscribe(topic)
        logger.info(
            "MQTT connected and subscribed to device topics",
            extra={"event": {"action": "mqtt.connected", "topics": topics}},
        )

    def _on_disconnect(self, _client, _userdata, _disconnect_flags, reason_code, _properties) -> None:
        self._connected = False
        if reason_code != 0:
            logger.warning(
                "MQTT disconnected unexpectedly with reason code %s",
                reason_code,
                extra={"event": {"action": "mqtt.disconnected", "reason_code": int(reason_code)}},
            )
        else:
            logger.info("MQTT disconnected cleanly", extra={"event": {"action": "mqtt.disconnected_clean"}})

    def _on_message(self, _client, _userdata, message) -> None:
        from app.services.mqtt_ingest_service import MqttIngestService

        session = get_session_factory()()
        try:
            payload_text = message.payload.decode("utf-8")
            MqttIngestService(session).process_message(message.topic, payload_text)
        except Exception:
            logger.exception("Failed to process MQTT message on %s", message.topic)
        finally:
            session.close()


def start_mqtt(settings: Settings) -> None:
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = MqttManager(settings)
        _manager.start()


def stop_mqtt() -> None:
    global _manager
    with _manager_lock:
        if _manager is not None:
            _manager.stop()
        _manager = None


def publish_json(topic: str, payload: dict, *, retain: bool = False) -> bool:
    with _manager_lock:
        if _manager is None:
            return False
        return _manager.publish_json(topic, payload, retain=retain)


def get_mqtt_status(settings: Settings) -> dict:
    with _manager_lock:
        return {
            "enabled": settings.mqtt_enabled,
            "host": settings.mqtt_host,
            "port": settings.mqtt_port,
            "started": _manager.started if _manager is not None else False,
            "connected": _manager.connected if _manager is not None else False,
        }
