from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.config import set_settings_override
from app.core.db import get_session_factory
from app.core.security import verify_password
from app.domain.audit_event import AuditEvent
from app.domain.device import Device
from app.domain.entity import Entity
from app.domain.user import User
from app.main import create_app
from app.services.mqtt_ingest_service import MqttIngestService
from app.services.site_service import SiteService
from app.services.user_service import UserService


def _build_settings(tmp_dir: str) -> Settings:
    return Settings(
        database_url=f"sqlite:///{Path(tmp_dir, 'alice-test.db').as_posix()}",
        log_dir=Path(tmp_dir, "logs").as_posix(),
        log_http_request_bodies=True,
        default_admin_email="admin@alice.systems",
        default_admin_password="change-me",
        default_admin_display_name="Alice Admin",
        mqtt_enabled=False,
    )


def _auth_headers(client: TestClient, settings: Settings) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": settings.default_admin_email, "password": settings.default_admin_password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _seed_entity() -> str:
    session = get_session_factory()()
    try:
        site = SiteService(session).get_or_create_default_site()
        now = datetime.now(UTC).replace(tzinfo=None)
        device = Device(
            id="dev_test_light_01",
            site_id=site.id,
            room_id=None,
            name="Test Relay Node",
            model="alice.relay.r1",
            device_type="relay_node",
            protocol="wifi-mqtt",
            status="online",
            provisioning_status="provisioned",
            fw_version="0.1.0",
            mqtt_client_id="relay-test-01",
            capability_descriptor_json="{}",
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
        entity = Entity(
            id="ent_test_light_01",
            site_id=site.id,
            room_id=None,
            device_id=device.id,
            capability_id="relay",
            kind="switch.relay",
            name="Test Light",
            slug="test-light",
            writable=1,
            traits_json="{}",
            created_at=now,
            updated_at=now,
        )
        session.add(device)
        session.add(entity)
        session.commit()
        return entity.id
    finally:
        session.close()


def test_health_endpoint() -> None:
    with TemporaryDirectory() as tmp_dir:
        settings = _build_settings(tmp_dir)
        with TestClient(create_app(settings)) as client:
            response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_request_logging_writes_http_events() -> None:
    with TemporaryDirectory() as tmp_dir:
        settings = _build_settings(tmp_dir)
        with TestClient(create_app(settings)) as client:
            response = client.get("/api/v1/devices")

        log_path = Path(tmp_dir, "logs", settings.log_filename)
        log_text = log_path.read_text(encoding="utf-8")

    assert response.status_code == 200
    assert "GET /api/v1/devices 200" in log_text
    assert "rid=req_" in log_text
    assert "X-Request-ID" in response.headers


def test_request_logging_redacts_sensitive_json_fields() -> None:
    with TemporaryDirectory() as tmp_dir:
        settings = _build_settings(tmp_dir)
        with TestClient(create_app(settings)) as client:
            response = client.post(
                "/api/v1/auth/login",
                json={"email": settings.default_admin_email, "password": settings.default_admin_password},
            )

        log_path = Path(tmp_dir, "logs", settings.log_filename)
        log_text = log_path.read_text(encoding="utf-8")

    assert response.status_code == 200
    assert "POST /api/v1/auth/login 200" in log_text
    assert "***REDACTED***" in log_text
    assert settings.default_admin_password not in log_text


def test_login_me_and_room_flow() -> None:
    with TemporaryDirectory() as tmp_dir:
        settings = _build_settings(tmp_dir)
        with TestClient(create_app(settings)) as client:
            root_response = client.get("/api/v1/")
            unauthorized_response = client.post("/api/v1/rooms", json={"name": "Kitchen"})
            headers = _auth_headers(client, settings)
            me_response = client.get("/api/v1/auth/me", headers=headers)
            create_response = client.post("/api/v1/rooms", json={"name": "Kitchen"}, headers=headers)
            list_response = client.get("/api/v1/rooms")
            audit_response = client.get("/api/v1/audit-events", headers=headers)

    assert root_response.status_code == 200
    assert root_response.json()["site_id"] == "site_home_01"
    assert unauthorized_response.status_code == 401
    assert me_response.status_code == 200
    assert me_response.json()["email"] == settings.default_admin_email
    assert create_response.status_code == 201
    assert create_response.json()["name"] == "Kitchen"
    assert len(list_response.json()["items"]) >= 1
    assert any(item["action"] == "room.created" for item in audit_response.json()["items"])


def test_entity_state_flow() -> None:
    with TemporaryDirectory() as tmp_dir:
        settings = _build_settings(tmp_dir)
        with TestClient(create_app(settings)) as client:
            headers = _auth_headers(client, settings)
            entity_id = _seed_entity()
            put_response = client.put(
                f"/api/v1/entities/{entity_id}/state",
                json={"value": {"on": True}, "source": "manual_test"},
                headers=headers,
            )
            get_response = client.get(f"/api/v1/entities/{entity_id}/state")
            audit_response = client.get("/api/v1/audit-events", headers=headers)

    assert put_response.status_code == 200
    assert put_response.json()["value"] == {"on": True}
    assert put_response.json()["version"] == 1
    assert get_response.status_code == 200
    assert get_response.json()["source"] == "manual_test"
    assert any(item["action"] == "entity_state.updated" for item in audit_response.json()["items"])


def test_mqtt_hello_and_state_projection() -> None:
    with TemporaryDirectory() as tmp_dir:
        settings = _build_settings(tmp_dir)
        with TestClient(create_app(settings)):
            session = get_session_factory()()
            try:
                service = MqttIngestService(session)
                service.process_message(
                    "alice/v1/device/dev_sensor_proto/hello",
                    """
                    {
                      "name": "Hall Sensor",
                      "model": "alice.sensor.env.s1",
                      "device_type": "sensor_node",
                      "fw_version": "0.1.0",
                      "capabilities": [
                        {"capability_id": "temperature", "kind": "sensor.temperature", "name": "Temperature", "slug": "temperature", "writable": 0, "traits": {"unit": "C"}},
                        {"capability_id": "motion", "kind": "sensor.motion", "name": "Motion", "slug": "motion", "writable": 0, "traits": {}}
                      ]
                    }
                    """,
                )
                service.process_message(
                    "alice/v1/device/dev_sensor_proto/state",
                    '{"capability":"temperature","celsius":21.2}',
                )
            finally:
                session.close()

            session = get_session_factory()()
            try:
                from app.repositories.device_repository import DeviceRepository
                from app.repositories.entity_repository import EntityRepository
                from app.repositories.entity_state_repository import EntityStateRepository

                device = DeviceRepository(session).get_by_id("dev_sensor_proto")
                entity = EntityRepository(session).get_by_device_and_capability("dev_sensor_proto", "temperature")
                state = EntityStateRepository(session).get(entity.id if entity else "")
            finally:
                session.close()

    assert device is not None
    assert device.name == "Hall Sensor"
    assert entity is not None
    assert state is not None
    assert '"celsius": 21.2' in state.value_json


def test_entity_command_publishes_to_mqtt(monkeypatch) -> None:
    published = {}

    def _fake_publish(topic: str, payload: dict, *, retain: bool = False) -> bool:
        published["topic"] = topic
        published["payload"] = payload
        published["retain"] = retain
        return True

    monkeypatch.setattr("app.services.command_service.publish_json", _fake_publish)

    with TemporaryDirectory() as tmp_dir:
        settings = _build_settings(tmp_dir)
        with TestClient(create_app(settings)) as client:
            headers = _auth_headers(client, settings)
            entity_id = _seed_entity()
            response = client.post(
                f"/api/v1/entities/{entity_id}/commands",
                json={"command": "switch.set", "params": {"on": True}},
                headers=headers,
            )

    assert response.status_code == 200
    assert response.json()["status"] == "queued"
    assert published["topic"] == "alice/v1/device/dev_test_light_01/cmd"
    assert published["payload"]["name"] == "switch.set"
    assert published["payload"]["params"] == {"on": True}


def test_auto_light_automation_publishes_command(monkeypatch) -> None:
    published = {}

    def _fake_publish(topic: str, payload: dict, *, retain: bool = False) -> bool:
        published["topic"] = topic
        published["payload"] = payload
        published["retain"] = retain
        return True

    monkeypatch.setattr("app.services.command_service.publish_json", _fake_publish)

    with TemporaryDirectory() as tmp_dir:
        settings = Settings(
            database_url=f"sqlite:///{Path(tmp_dir, 'alice-test.db').as_posix()}",
            default_admin_email="admin@alice.systems",
            default_admin_password="change-me",
            default_admin_display_name="Alice Admin",
            mqtt_enabled=False,
            auto_light_enabled=True,
            auto_light_sensor_entity_id="ent_dev_sensor_hall_01_illuminance",
            auto_light_target_entity_id="ent_dev_light_bench_01_relay",
            auto_light_on_lux=120.0,
            auto_light_off_lux=220.0,
            auto_light_block_on_during_daytime=False,
        )
        with TestClient(create_app(settings)):
            session = get_session_factory()()
            try:
                service = MqttIngestService(session)
                service.process_message(
                    "alice/v1/device/dev_sensor_hall_01/hello",
                    """
                    {
                      "name": "Hall Sensor",
                      "model": "alice.sensor.env.s1",
                      "device_type": "sensor_node",
                      "fw_version": "0.1.0"
                    }
                    """,
                )
                service.process_message(
                    "alice/v1/device/dev_light_bench_01/hello",
                    """
                    {
                      "name": "Bench Light",
                      "model": "alice.relay.r1",
                      "device_type": "relay_node",
                      "fw_version": "0.1.0"
                    }
                    """,
                )
                service.process_message(
                    "alice/v1/device/dev_sensor_hall_01/state",
                    '{"capability":"illuminance","lux":80.0,"raw":3200}',
                )
            finally:
                session.close()

    assert published["topic"] == "alice/v1/device/dev_light_bench_01/cmd"
    assert published["payload"]["name"] == "switch.set"
    assert published["payload"]["params"] == {"on": True}


def test_auto_light_raw_threshold_publishes_command(monkeypatch) -> None:
    published = {}

    def _fake_publish(topic: str, payload: dict, *, retain: bool = False) -> bool:
        published["topic"] = topic
        published["payload"] = payload
        published["retain"] = retain
        return True

    monkeypatch.setattr("app.services.command_service.publish_json", _fake_publish)

    with TemporaryDirectory() as tmp_dir:
        settings = Settings(
            database_url=f"sqlite:///{Path(tmp_dir, 'alice-test.db').as_posix()}",
            default_admin_email="admin@alice.systems",
            default_admin_password="change-me",
            default_admin_display_name="Alice Admin",
            mqtt_enabled=False,
            auto_light_enabled=True,
            auto_light_sensor_entity_id="ent_dev_sensor_hall_01_illuminance",
            auto_light_target_entity_id="ent_dev_light_bench_01_relay",
            auto_light_mode="raw_high_turn_on",
            auto_light_on_raw=3000.0,
            auto_light_off_raw=2600.0,
            auto_light_block_on_during_daytime=False,
        )
        with TestClient(create_app(settings)):
            session = get_session_factory()()
            try:
                service = MqttIngestService(session)
                service.process_message(
                    "alice/v1/device/dev_sensor_hall_01/hello",
                    """
                    {
                      "name": "Hall Sensor",
                      "model": "alice.sensor.env.s1",
                      "device_type": "sensor_node",
                      "fw_version": "0.1.0"
                    }
                    """,
                )
                service.process_message(
                    "alice/v1/device/dev_light_bench_01/hello",
                    """
                    {
                      "name": "Bench Light",
                      "model": "alice.relay.r1",
                      "device_type": "relay_node",
                      "fw_version": "0.1.0"
                    }
                    """,
                )
                service.process_message(
                    "alice/v1/device/dev_sensor_hall_01/state",
                    '{"capability":"illuminance","lux":100.0,"raw":3200}',
                )
            finally:
                session.close()

    assert published["topic"] == "alice/v1/device/dev_light_bench_01/cmd"
    assert published["payload"]["name"] == "switch.set"
    assert published["payload"]["params"] == {"on": True}


def test_list_entity_states_endpoint() -> None:
    with TemporaryDirectory() as tmp_dir:
        settings = _build_settings(tmp_dir)
        with TestClient(create_app(settings)) as client:
            headers = _auth_headers(client, settings)
            entity_id = _seed_entity()
            put_response = client.put(
                f"/api/v1/entities/{entity_id}/state",
                json={"value": {"on": True}, "source": "manual_test"},
                headers=headers,
            )
            states_response = client.get("/api/v1/entities/states")

    assert put_response.status_code == 200
    assert states_response.status_code == 200
    assert any(item["entity_id"] == entity_id for item in states_response.json()["items"])


def test_auto_light_settings_api_drives_automation(monkeypatch) -> None:
    published = {}

    def _fake_publish(topic: str, payload: dict, *, retain: bool = False) -> bool:
        published["topic"] = topic
        published["payload"] = payload
        published["retain"] = retain
        return True

    monkeypatch.setattr("app.services.command_service.publish_json", _fake_publish)

    with TemporaryDirectory() as tmp_dir:
        settings = _build_settings(tmp_dir)
        with TestClient(create_app(settings)) as client:
            headers = _auth_headers(client, settings)
            update_response = client.put(
                "/api/v1/system/auto-light",
                json={
                    "enabled": True,
                    "sensor_entity_id": "ent_dev_sensor_hall_01_illuminance",
                    "target_entity_id": "ent_dev_light_bench_01_relay",
                    "mode": "raw_high_turn_on",
                    "on_lux": 120.0,
                    "off_lux": 220.0,
                    "on_raw": 3000.0,
                    "off_raw": 2600.0,
                    "block_on_during_daytime": False,
                    "daytime_start_hour": 7,
                    "daytime_end_hour": 18,
                },
                headers=headers,
            )
            get_response = client.get("/api/v1/system/auto-light", headers=headers)
            session = get_session_factory()()
            try:
                service = MqttIngestService(session)
                service.process_message(
                    "alice/v1/device/dev_sensor_hall_01/hello",
                    '{"name":"Hall Sensor","model":"alice.sensor.env.s1","device_type":"sensor_node","fw_version":"0.1.1"}',
                )
                service.process_message(
                    "alice/v1/device/dev_light_bench_01/hello",
                    '{"name":"Bench Light","model":"alice.relay.r1","device_type":"relay_node","fw_version":"0.1.1"}',
                )
                service.process_message(
                    "alice/v1/device/dev_sensor_hall_01/state",
                    '{"capability":"illuminance","raw":3200,"lux":1000}',
                )
            finally:
                session.close()

    assert update_response.status_code == 200
    assert get_response.status_code == 200
    assert get_response.json()["source"] == "db"
    assert published["topic"] == "alice/v1/device/dev_light_bench_01/cmd"
    assert published["payload"]["params"] == {"on": True}


def test_auto_light_daytime_guard_suppresses_turn_on(monkeypatch) -> None:
    published = {}

    def _fake_publish(topic: str, payload: dict, *, retain: bool = False) -> bool:
        published["topic"] = topic
        published["payload"] = payload
        published["retain"] = retain
        return True

    monkeypatch.setattr("app.services.command_service.publish_json", _fake_publish)
    monkeypatch.setattr(
        "app.services.automation_service.AutomationService._current_local_hour",
        lambda self: 13,
    )

    with TemporaryDirectory() as tmp_dir:
        settings = Settings(
            database_url=f"sqlite:///{Path(tmp_dir, 'alice-test.db').as_posix()}",
            default_admin_email="admin@alice.systems",
            default_admin_password="change-me",
            default_admin_display_name="Alice Admin",
            mqtt_enabled=False,
            auto_light_enabled=True,
            auto_light_sensor_entity_id="ent_dev_sensor_hall_01_illuminance",
            auto_light_target_entity_id="ent_dev_light_bench_01_relay",
            auto_light_on_lux=120.0,
            auto_light_off_lux=220.0,
            auto_light_block_on_during_daytime=True,
            auto_light_daytime_start_hour=7,
            auto_light_daytime_end_hour=18,
        )
        with TestClient(create_app(settings)):
            session = get_session_factory()()
            try:
                service = MqttIngestService(session)
                service.process_message(
                    "alice/v1/device/dev_sensor_hall_01/hello",
                    """
                    {
                      "name": "Hall Sensor",
                      "model": "alice.sensor.env.s1",
                      "device_type": "sensor_node",
                      "fw_version": "0.1.0"
                    }
                    """,
                )
                service.process_message(
                    "alice/v1/device/dev_light_bench_01/hello",
                    """
                    {
                      "name": "Bench Light",
                      "model": "alice.relay.r1",
                      "device_type": "relay_node",
                      "fw_version": "0.1.0"
                    }
                    """,
                )
                service.process_message(
                    "alice/v1/device/dev_sensor_hall_01/state",
                    '{"capability":"illuminance","lux":80.0,"raw":3200}',
                )
            finally:
                session.close()

    assert published == {}


def test_device_offline_timeout_marks_device_offline() -> None:
    with TemporaryDirectory() as tmp_dir:
        settings = Settings(
            database_url=f"sqlite:///{Path(tmp_dir, 'alice-test.db').as_posix()}",
            log_dir=Path(tmp_dir, "logs").as_posix(),
            default_admin_email="admin@alice.systems",
            default_admin_password="change-me",
            default_admin_display_name="Alice Admin",
            mqtt_enabled=False,
            device_offline_timeout_seconds=30,
        )
        with TestClient(create_app(settings)) as client:
            session = get_session_factory()()
            try:
                site = SiteService(session).get_or_create_default_site()
                stale_time = datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=40)
                device = Device(
                    id="dev_stale_01",
                    site_id=site.id,
                    room_id=None,
                    name="Stale Device",
                    model="alice.relay.r1",
                    device_type="relay_node",
                    protocol="wifi-mqtt",
                    status="online",
                    provisioning_status="provisioned",
                    fw_version="0.1.0",
                    mqtt_client_id="stale-01",
                    capability_descriptor_json="[]",
                    last_seen_at=stale_time,
                    created_at=stale_time,
                    updated_at=stale_time,
                )
                session.add(device)
                session.commit()
            finally:
                session.close()

            response = client.get("/api/v1/devices")

    assert response.status_code == 200
    assert response.json()["items"][0]["status"] == "offline"


def test_mqtt_ack_records_audit_event() -> None:
    with TemporaryDirectory() as tmp_dir:
        settings = _build_settings(tmp_dir)
        with TestClient(create_app(settings)):
            session = get_session_factory()()
            try:
                service = MqttIngestService(session)
                service.process_message(
                    "alice/v1/device/dev_light_bench_01/hello",
                    '{"name":"Bench Light","model":"alice.relay.r1","device_type":"relay_node","fw_version":"0.1.1"}',
                )
                service.process_message(
                    "alice/v1/device/dev_light_bench_01/ack",
                    '{"cmd_id":"cmd_123","target_entity_id":"ent_dev_light_bench_01_relay","status":"applied","name":"switch.set","params":{"on":true},"state":{"on":true}}',
                )
            finally:
                session.close()

            session = get_session_factory()()
            try:
                events = list(session.query(AuditEvent).all())
            finally:
                session.close()

    assert any(event.action == "entity.command_acknowledged" for event in events)


def test_stack_health_reports_broker_devices_and_latest_ack() -> None:
    with TemporaryDirectory() as tmp_dir:
        settings = _build_settings(tmp_dir)
        with TestClient(create_app(settings)) as client:
            headers = _auth_headers(client, settings)
            session = get_session_factory()()
            try:
                service = MqttIngestService(session)
                service.process_message(
                    "alice/v1/device/dev_sensor_hall_01/hello",
                    '{"name":"Hall Sensor","model":"alice.sensor.env.s1","device_type":"sensor_node","fw_version":"0.1.1"}',
                )
                service.process_message(
                    "alice/v1/device/dev_light_bench_01/hello",
                    '{"name":"Bench Light","model":"alice.relay.r1","device_type":"relay_node","fw_version":"0.1.1"}',
                )
                service.process_message(
                    "alice/v1/device/dev_light_bench_01/ack",
                    '{"cmd_id":"cmd_123","target_entity_id":"ent_dev_light_bench_01_relay","status":"applied","name":"switch.set","params":{"on":true},"state":{"on":true}}',
                )
            finally:
                session.close()

            response = client.get("/api/v1/system/stack-health", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["api_status"] == "ok"
    assert body["devices"]["total"] == 2
    assert body["latest_command_ack"]["action"] == "entity.command_acknowledged"
    assert body["latest_command_ack"]["metadata"]["status"] == "applied"


def test_mqtt_retained_state_rehydrates_after_hello() -> None:
    with TemporaryDirectory() as tmp_dir:
        settings = _build_settings(tmp_dir)
        with TestClient(create_app(settings)):
            session = get_session_factory()()
            try:
                service = MqttIngestService(session)
                service.process_message(
                    "alice/v1/device/dev_sensor_hall_01/state",
                    '{"capability":"temperature","celsius":22.4}',
                )
                service.process_message(
                    "alice/v1/device/dev_sensor_hall_01/hello",
                    """
                    {
                      "name": "Hall Sensor",
                      "model": "alice.sensor.env.s1",
                      "device_type": "sensor_node",
                      "fw_version": "0.1.1",
                      "capabilities": [
                        {"capability_id": "temperature", "kind": "sensor.temperature", "name": "Temperature", "slug": "temperature", "writable": 0, "traits": {"unit": "C"}}
                      ]
                    }
                    """,
                )
            finally:
                session.close()

            session = get_session_factory()()
            try:
                from app.repositories.entity_repository import EntityRepository
                from app.repositories.entity_state_repository import EntityStateRepository

                entity = EntityRepository(session).get_by_device_and_capability(
                    "dev_sensor_hall_01", "temperature"
                )
                state = EntityStateRepository(session).get(entity.id if entity else "")
            finally:
                session.close()

    assert entity is not None
    assert state is not None
    assert '"celsius": 22.4' in state.value_json


def test_dashboard_websocket_receives_audit_events() -> None:
    with TemporaryDirectory() as tmp_dir:
        settings = _build_settings(tmp_dir)
        with TestClient(create_app(settings)) as client:
            headers = _auth_headers(client, settings)
            token = headers["Authorization"].removeprefix("Bearer ").strip()
            entity_id = _seed_entity()

            with client.websocket_connect(f"/api/v1/ws/dashboard?token={token}") as websocket:
                first = websocket.receive_json()
                assert first["type"] == "connected"

                response = client.put(
                    f"/api/v1/entities/{entity_id}/state",
                    json={"value": {"on": True}, "source": "manual_test"},
                    headers=headers,
                )
                assert response.status_code == 200

                event = websocket.receive_json()
                while event.get("type") == "ping":
                    event = websocket.receive_json()

    assert event["type"] == "audit_event"
    assert event["action"] == "entity_state.updated"


def test_sync_default_admin_updates_existing_admin_from_env_values() -> None:
    with TemporaryDirectory() as tmp_dir:
        settings = _build_settings(tmp_dir)
        with TestClient(create_app(settings)):
            session = get_session_factory()()
            try:
                site = SiteService(session).get_or_create_default_site()
                service = UserService(session)
                original = service.ensure_default_admin(site_id=site.id)

                updated_settings = Settings(
                    database_url=settings.database_url,
                    log_dir=settings.log_dir,
                    default_admin_email="founder@alice.systems",
                    default_admin_password="new-password-123",
                    default_admin_display_name="Founder Admin",
                    mqtt_enabled=False,
                )
                set_settings_override(updated_settings)
                try:
                    synced, action = service.sync_default_admin(site_id=site.id)
                finally:
                    set_settings_override(None)
            finally:
                session.close()

            session = get_session_factory()()
            try:
                users = session.query(User).all()
            finally:
                session.close()

    assert action == "migrated_single_admin"
    assert synced.email == "founder@alice.systems"
    assert synced.display_name == "Founder Admin"
    assert len(users) == 1
    assert users[0].id == original.id
    assert verify_password("new-password-123", users[0].password_hash)
