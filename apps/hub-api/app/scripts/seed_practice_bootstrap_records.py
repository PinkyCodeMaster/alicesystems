from __future__ import annotations

from datetime import UTC, datetime
import json

from sqlalchemy import select

from app.core.db import close_engine, get_session_factory, init_db
from app.core.security import hash_password
from app.domain.device_bootstrap_record import DeviceBootstrapRecord
from app.services.site_service import SiteService


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _ensure_bootstrap_record(
    *,
    session,
    bootstrap_id: str,
    model: str,
    device_type: str,
    setup_code: str,
    default_device_id: str,
    metadata: dict,
) -> DeviceBootstrapRecord:
    record = session.scalar(select(DeviceBootstrapRecord).where(DeviceBootstrapRecord.id == bootstrap_id))
    now = _now()
    metadata_json = json.dumps(metadata, sort_keys=True)

    if record is None:
        record = DeviceBootstrapRecord(
            id=bootstrap_id,
            model=model,
            device_type=device_type,
            hardware_revision=None,
            default_device_id=default_device_id,
            setup_code_hash=hash_password(setup_code),
            status="claimable",
            claimed_device_id=None,
            metadata_json=metadata_json,
            created_at=now,
            updated_at=now,
            claimed_at=None,
        )
        session.add(record)
    elif record.status != "claimed":
        record.model = model
        record.device_type = device_type
        record.default_device_id = default_device_id
        record.setup_code_hash = hash_password(setup_code)
        record.metadata_json = metadata_json
        record.updated_at = now

    session.commit()
    session.refresh(record)
    return record


def main() -> None:
    init_db()
    session = get_session_factory()()
    try:
        site = SiteService(session).get_or_create_default_site()
        _ensure_bootstrap_record(
            session=session,
            bootstrap_id="boot_mock_sensor_01",
            model="alice.sensor.env.s1",
            device_type="sensor_node",
            setup_code="482913",
            default_device_id="dev_mock_sensor_01",
            metadata={"seeded_by": "seed_practice_bootstrap_records", "hardware": "docker-mock-sensor"},
        )
        _ensure_bootstrap_record(
            session=session,
            bootstrap_id="boot_mock_relay_01",
            model="alice.relay.r1",
            device_type="relay_node",
            setup_code="918274",
            default_device_id="dev_mock_relay_01",
            metadata={"seeded_by": "seed_practice_bootstrap_records", "hardware": "docker-mock-relay"},
        )

        print("Practice bootstrap seed complete.")
        print(f"Site: {site.id} ({site.name})")
        print("No user, room, device, or entity demo data was created.")
        print("Bootstrap records: boot_mock_sensor_01 (482913), boot_mock_relay_01 (918274)")
    finally:
        session.close()
        close_engine()


if __name__ == "__main__":
    main()
