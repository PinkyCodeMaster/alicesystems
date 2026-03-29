from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import json
import re
import secrets
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password, verify_password
from app.domain.device import Device
from app.domain.device_bootstrap_record import DeviceBootstrapRecord
from app.domain.device_credential import DeviceCredential
from app.domain.provisioning_session import ProvisioningSession
from app.domain.user import User
from app.repositories.device_bootstrap_repository import DeviceBootstrapRepository
from app.repositories.device_credential_repository import DeviceCredentialRepository
from app.repositories.device_repository import DeviceRepository
from app.repositories.provisioning_session_repository import ProvisioningSessionRepository
from app.repositories.room_repository import RoomRepository
from app.services.audit_service import AuditService


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _slug_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _default_device_id(bootstrap_id: str) -> str:
    compact = _slug_token(bootstrap_id)[:52] or uuid4().hex[:12]
    return f"dev_{compact}"


def _default_device_name(model: str) -> str:
    tail = model.split(".")[-1].replace("_", " ").replace("-", " ").strip()
    return tail.title() or "Alice Device"


@dataclass
class ProvisioningSessionResult:
    session_id: str
    bootstrap_id: str
    status: str
    claim_token: str
    expires_at: datetime
    requested_device_name: str | None
    room_id: str | None


@dataclass
class ProvisioningSessionStatusResult:
    session_id: str
    bootstrap_id: str
    status: str
    expires_at: datetime
    requested_device_name: str | None
    room_id: str | None
    claimed_device_id: str | None
    completed_at: datetime | None


@dataclass
class ProvisioningRuntimeConfig:
    session_id: str
    bootstrap_id: str
    device_id: str
    site_id: str
    room_id: str | None
    device_name: str
    model: str
    device_type: str
    protocol: str
    provisioning_status: str
    mqtt_host: str
    mqtt_port: int
    mqtt_topic_prefix: str
    mqtt_client_id: str
    mqtt_username: str
    mqtt_password: str


class ProvisioningService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.bootstrap_repo = DeviceBootstrapRepository(db)
        self.session_repo = ProvisioningSessionRepository(db)
        self.device_repo = DeviceRepository(db)
        self.device_credential_repo = DeviceCredentialRepository(db)
        self.room_repo = RoomRepository(db)
        self.audit_service = AuditService(db)

    def create_bootstrap_record(
        self,
        *,
        bootstrap_id: str,
        model: str,
        device_type: str,
        setup_code: str,
        hardware_revision: str | None,
        default_device_id: str | None,
        metadata: dict,
        actor: User,
    ) -> DeviceBootstrapRecord:
        bootstrap_id = bootstrap_id.strip()
        if self.bootstrap_repo.get_by_id(bootstrap_id) is not None:
            raise ValueError("A bootstrap record with that ID already exists.")

        now = _now()
        record = DeviceBootstrapRecord(
            id=bootstrap_id,
            model=model.strip(),
            device_type=device_type.strip(),
            hardware_revision=hardware_revision.strip() if hardware_revision else None,
            default_device_id=default_device_id.strip() if default_device_id else None,
            setup_code_hash=hash_password(setup_code.strip()),
            status="claimable",
            claimed_device_id=None,
            metadata_json=json.dumps(metadata, sort_keys=True),
            created_at=now,
            updated_at=now,
            claimed_at=None,
        )
        saved = self.bootstrap_repo.save(record)
        self.audit_service.record_event(
            site_id=actor.site_id,
            actor_type="user",
            actor_id=actor.id,
            action="provisioning.bootstrap_registered",
            target_type="device_bootstrap",
            target_id=saved.id,
            severity="info",
            metadata_json=json.dumps(
                {
                    "model": saved.model,
                    "device_type": saved.device_type,
                    "default_device_id": saved.default_device_id,
                }
            ),
        )
        return saved

    def start_claim_session(
        self,
        *,
        bootstrap_id: str,
        setup_code: str,
        room_id: str | None,
        requested_device_name: str | None,
        actor: User,
    ) -> ProvisioningSessionResult:
        now = _now()
        bootstrap = self._require_bootstrap(bootstrap_id)
        self._expire_if_stale(bootstrap_id, now=now)

        if bootstrap.status == "claimed":
            raise ValueError("That device has already been claimed.")
        if not verify_password(setup_code.strip(), bootstrap.setup_code_hash):
            raise ValueError("Invalid setup code.")
        if room_id is not None:
            room = self.room_repo.get_by_id(room_id)
            if room is None or room.site_id != actor.site_id:
                raise ValueError("Room not found.")

        active = self.session_repo.get_active_for_bootstrap(bootstrap.id, now=now)
        if active is not None:
            raise ValueError("A claim session is already active for that device.")

        settings = get_settings()
        session_id = f"prov_{uuid4().hex[:16]}"
        claim_token = secrets.token_urlsafe(24)
        expires_at = now + timedelta(minutes=settings.provisioning_session_expiry_minutes)
        session = ProvisioningSession(
            id=session_id,
            site_id=actor.site_id,
            created_by_user_id=actor.id,
            bootstrap_id=bootstrap.id,
            room_id=room_id,
            requested_device_name=requested_device_name.strip() if requested_device_name else None,
            claim_token_hash=hash_password(claim_token),
            status="pending",
            expires_at=expires_at,
            claimed_device_id=None,
            created_at=now,
            updated_at=now,
            completed_at=None,
        )
        saved = self.session_repo.save(session)
        self.audit_service.record_event(
            site_id=actor.site_id,
            actor_type="user",
            actor_id=actor.id,
            action="provisioning.session_started",
            target_type="device_bootstrap",
            target_id=bootstrap.id,
            severity="info",
            metadata_json=json.dumps({"session_id": saved.id, "expires_at": saved.expires_at.isoformat()}),
        )
        return ProvisioningSessionResult(
            session_id=saved.id,
            bootstrap_id=saved.bootstrap_id,
            status=saved.status,
            claim_token=claim_token,
            expires_at=saved.expires_at,
            requested_device_name=saved.requested_device_name,
            room_id=saved.room_id,
        )

    def get_session_status(self, *, session_id: str, actor: User) -> ProvisioningSessionStatusResult:
        session = self.session_repo.get_by_id(session_id)
        if session is None or session.site_id != actor.site_id:
            raise ValueError("Provisioning session not found.")

        self._expire_if_stale(session.bootstrap_id, now=_now())
        fresh = self.session_repo.get_by_id(session_id)
        assert fresh is not None
        return ProvisioningSessionStatusResult(
            session_id=fresh.id,
            bootstrap_id=fresh.bootstrap_id,
            status=fresh.status,
            expires_at=fresh.expires_at,
            requested_device_name=fresh.requested_device_name,
            room_id=fresh.room_id,
            claimed_device_id=fresh.claimed_device_id,
            completed_at=fresh.completed_at,
        )

    def complete_claim(
        self,
        *,
        bootstrap_id: str,
        claim_token: str,
        fw_version: str | None,
        protocol: str,
        mqtt_client_id: str | None,
    ) -> ProvisioningRuntimeConfig:
        now = _now()
        bootstrap = self._require_bootstrap(bootstrap_id)
        session = self.session_repo.get_active_for_bootstrap(bootstrap.id, now=now)
        if session is None:
            latest = self.session_repo.get_latest_for_bootstrap(bootstrap.id)
            if latest is not None and latest.status == "claimed":
                raise ValueError("That device has already completed provisioning.")
            raise ValueError("No active claim session exists for that device.")
        if not verify_password(claim_token.strip(), session.claim_token_hash):
            raise ValueError("Invalid claim token.")

        device_id = bootstrap.default_device_id or _default_device_id(bootstrap.id)
        mqtt_client_id = mqtt_client_id.strip() if mqtt_client_id else device_id
        device = self.device_repo.get_by_id(device_id)
        device_name = session.requested_device_name or (device.name if device is not None else None) or _default_device_name(
            bootstrap.model
        )
        if device is None:
            device = Device(
                id=device_id,
                site_id=session.site_id,
                room_id=session.room_id,
                name=device_name,
                model=bootstrap.model,
                device_type=bootstrap.device_type,
                protocol=protocol.strip(),
                status="offline",
                provisioning_status="provisioned",
                fw_version=fw_version.strip() if fw_version else None,
                mqtt_client_id=mqtt_client_id,
                capability_descriptor_json="[]",
                last_seen_at=None,
                created_at=now,
                updated_at=now,
            )
        else:
            device.room_id = session.room_id
            device.name = device_name
            device.model = bootstrap.model
            device.device_type = bootstrap.device_type
            device.protocol = protocol.strip()
            device.provisioning_status = "provisioned"
            device.fw_version = fw_version.strip() if fw_version else device.fw_version
            device.mqtt_client_id = mqtt_client_id
            device.updated_at = now

        saved_device = self.device_repo.save(device)

        mqtt_username = f"device.{_slug_token(saved_device.id)[:96] or saved_device.id}"
        mqtt_password = secrets.token_urlsafe(18)
        credential = self.device_credential_repo.get_by_device_id(saved_device.id)
        if credential is None:
            credential = DeviceCredential(
                device_id=saved_device.id,
                mqtt_username=mqtt_username,
                mqtt_password_hash=hash_password(mqtt_password),
                issued_at=now,
                updated_at=now,
            )
        else:
            credential.mqtt_username = mqtt_username
            credential.mqtt_password_hash = hash_password(mqtt_password)
            credential.updated_at = now

        self.device_credential_repo.save(credential)

        bootstrap.status = "claimed"
        bootstrap.claimed_device_id = saved_device.id
        bootstrap.claimed_at = now
        bootstrap.updated_at = now
        self.bootstrap_repo.save(bootstrap)

        session.status = "claimed"
        session.claimed_device_id = saved_device.id
        session.updated_at = now
        session.completed_at = now
        self.session_repo.save(session)

        self.audit_service.record_event(
            site_id=session.site_id,
            actor_type="device_bootstrap",
            actor_id=bootstrap.id,
            action="provisioning.claim_completed",
            target_type="device",
            target_id=saved_device.id,
            severity="info",
            metadata_json=json.dumps(
                {
                    "session_id": session.id,
                    "mqtt_client_id": saved_device.mqtt_client_id,
                    "protocol": saved_device.protocol,
                }
            ),
        )

        settings = get_settings()
        return ProvisioningRuntimeConfig(
            session_id=session.id,
            bootstrap_id=bootstrap.id,
            device_id=saved_device.id,
            site_id=saved_device.site_id,
            room_id=saved_device.room_id,
            device_name=saved_device.name,
            model=saved_device.model,
            device_type=saved_device.device_type,
            protocol=saved_device.protocol,
            provisioning_status=saved_device.provisioning_status,
            mqtt_host=settings.mqtt_host,
            mqtt_port=settings.mqtt_port,
            mqtt_topic_prefix=settings.mqtt_topic_prefix,
            mqtt_client_id=saved_device.mqtt_client_id,
            mqtt_username=credential.mqtt_username,
            mqtt_password=mqtt_password,
        )

    def _expire_if_stale(self, bootstrap_id: str, *, now: datetime) -> None:
        session = self.session_repo.get_latest_for_bootstrap(bootstrap_id)
        if session is None or session.status != "pending" or session.expires_at > now:
            return
        session.status = "expired"
        session.updated_at = now
        self.session_repo.save(session)

    def _require_bootstrap(self, bootstrap_id: str) -> DeviceBootstrapRecord:
        bootstrap = self.bootstrap_repo.get_by_id(bootstrap_id.strip())
        if bootstrap is None:
            raise ValueError("Bootstrap record not found.")
        return bootstrap
