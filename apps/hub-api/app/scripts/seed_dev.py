from __future__ import annotations

from datetime import UTC, datetime
import json

from sqlalchemy import select

from app.core.db import close_engine, get_session_factory, init_db
from app.domain.device import Device
from app.domain.entity import Entity
from app.services.entity_state_service import EntityStateService
from app.services.room_service import RoomService
from app.services.site_service import SiteService
from app.services.user_service import UserService


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _ensure_device(
    *,
    session,
    device_id: str,
    site_id: str,
    room_id: str | None,
    name: str,
    model: str,
    device_type: str,
    mqtt_client_id: str,
) -> Device:
    device = session.scalar(select(Device).where(Device.id == device_id))
    now = _now()
    if device is None:
        device = Device(
            id=device_id,
            site_id=site_id,
            room_id=room_id,
            name=name,
            model=model,
            device_type=device_type,
            protocol="wifi-mqtt",
            status="offline",
            provisioning_status="seeded_dev",
            fw_version="0.1.0",
            mqtt_client_id=mqtt_client_id,
            capability_descriptor_json="{}",
            last_seen_at=None,
            created_at=now,
            updated_at=now,
        )
        session.add(device)
    else:
        device.room_id = room_id
        device.name = name
        device.model = model
        device.device_type = device_type
        device.mqtt_client_id = mqtt_client_id
        device.updated_at = now
    session.commit()
    session.refresh(device)
    return device


def _ensure_entity(
    *,
    session,
    entity_id: str,
    site_id: str,
    room_id: str | None,
    device_id: str,
    capability_id: str,
    kind: str,
    name: str,
    slug: str,
    writable: int,
    traits: dict,
) -> Entity:
    entity = session.scalar(select(Entity).where(Entity.id == entity_id))
    now = _now()
    if entity is None:
        entity = Entity(
            id=entity_id,
            site_id=site_id,
            room_id=room_id,
            device_id=device_id,
            capability_id=capability_id,
            kind=kind,
            name=name,
            slug=slug,
            writable=writable,
            traits_json=json.dumps(traits, sort_keys=True),
            created_at=now,
            updated_at=now,
        )
        session.add(entity)
    else:
        entity.room_id = room_id
        entity.device_id = device_id
        entity.kind = kind
        entity.name = name
        entity.slug = slug
        entity.writable = writable
        entity.traits_json = json.dumps(traits, sort_keys=True)
        entity.updated_at = now
    session.commit()
    session.refresh(entity)
    return entity


def main() -> None:
    init_db()
    session = get_session_factory()()
    try:
        site = SiteService(session).get_or_create_default_site()
        admin = UserService(session).ensure_default_admin(site_id=site.id)
        room_service = RoomService(session)

        office, _ = room_service.create_room(name="Office", actor_id=admin.id)
        living_room, _ = room_service.create_room(name="Living Room", actor_id=admin.id)

        sensor_device = _ensure_device(
            session=session,
            device_id="dev_seed_sensor_01",
            site_id=site.id,
            room_id=office.id,
            name="Seed Sensor Node",
            model="alice.sensor.env.s1",
            device_type="sensor_node",
            mqtt_client_id="seed-sensor-01",
        )
        light_device = _ensure_device(
            session=session,
            device_id="dev_seed_light_01",
            site_id=site.id,
            room_id=living_room.id,
            name="Seed Light Node",
            model="alice.relay.r1",
            device_type="relay_node",
            mqtt_client_id="seed-light-01",
        )

        temp_entity = _ensure_entity(
            session=session,
            entity_id="ent_seed_temp_01",
            site_id=site.id,
            room_id=office.id,
            device_id=sensor_device.id,
            capability_id="temperature",
            kind="sensor.temperature",
            name="Office Temperature",
            slug="office-temperature",
            writable=0,
            traits={"unit": "C"},
        )
        motion_entity = _ensure_entity(
            session=session,
            entity_id="ent_seed_motion_01",
            site_id=site.id,
            room_id=office.id,
            device_id=sensor_device.id,
            capability_id="motion",
            kind="sensor.motion",
            name="Office Motion",
            slug="office-motion",
            writable=0,
            traits={},
        )
        light_entity = _ensure_entity(
            session=session,
            entity_id="ent_seed_light_01",
            site_id=site.id,
            room_id=living_room.id,
            device_id=light_device.id,
            capability_id="relay",
            kind="switch.relay",
            name="Living Room Test Light",
            slug="living-room-test-light",
            writable=1,
            traits={},
        )

        state_service = EntityStateService(session)
        if state_service.get_state(temp_entity.id) is None:
            state_service.set_state(
                entity_id=temp_entity.id,
                value={"celsius": 20.5},
                source="seed_dev",
                actor_id=admin.id,
            )
        if state_service.get_state(motion_entity.id) is None:
            state_service.set_state(
                entity_id=motion_entity.id,
                value={"motion": False},
                source="seed_dev",
                actor_id=admin.id,
            )
        if state_service.get_state(light_entity.id) is None:
            state_service.set_state(
                entity_id=light_entity.id,
                value={"on": False},
                source="seed_dev",
                actor_id=admin.id,
            )

        print("Seed complete.")
        print(f"Site: {site.id} ({site.name})")
        print(f"Admin: {admin.email}")
        print(f"Rooms: {office.name}, {living_room.name}")
        print("Devices: dev_seed_sensor_01, dev_seed_light_01")
        print("Entities: ent_seed_temp_01, ent_seed_motion_01, ent_seed_light_01")
    finally:
        session.close()
        close_engine()


if __name__ == "__main__":
    main()
