from app.api.deps import get_current_user, get_db
from app.domain.user import User
from app.schemas.provisioning import (
    DeviceBootstrapRecordCreateRequest,
    DeviceBootstrapRecordItem,
    ProvisioningClaimCompleteRequest,
    ProvisioningRuntimeConfigResponse,
    ProvisioningSessionCreateRequest,
    ProvisioningSessionResponse,
    ProvisioningSessionStatusResponse,
)
from app.services.provisioning_service import ProvisioningService
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

router = APIRouter()


@router.post("/bootstrap-records", response_model=DeviceBootstrapRecordItem, status_code=status.HTTP_201_CREATED)
def create_bootstrap_record(
    payload: DeviceBootstrapRecordCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DeviceBootstrapRecordItem:
    try:
        record = ProvisioningService(db).create_bootstrap_record(
            bootstrap_id=payload.bootstrap_id,
            model=payload.model,
            device_type=payload.device_type,
            setup_code=payload.setup_code,
            hardware_revision=payload.hardware_revision,
            default_device_id=payload.default_device_id,
            metadata=payload.metadata,
            actor=current_user,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return DeviceBootstrapRecordItem.model_validate(record)


@router.post("/sessions", response_model=ProvisioningSessionResponse, status_code=status.HTTP_201_CREATED)
def create_provisioning_session(
    payload: ProvisioningSessionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProvisioningSessionResponse:
    try:
        result = ProvisioningService(db).start_claim_session(
            bootstrap_id=payload.bootstrap_id,
            setup_code=payload.setup_code,
            room_id=payload.room_id,
            requested_device_name=payload.requested_device_name,
            actor=current_user,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ProvisioningSessionResponse(**result.__dict__)


@router.get("/sessions/{session_id}", response_model=ProvisioningSessionStatusResponse)
def get_provisioning_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProvisioningSessionStatusResponse:
    try:
        result = ProvisioningService(db).get_session_status(session_id=session_id, actor=current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ProvisioningSessionStatusResponse(**result.__dict__)


@router.post("/claim/complete", response_model=ProvisioningRuntimeConfigResponse)
def complete_claim(
    payload: ProvisioningClaimCompleteRequest,
    db: Session = Depends(get_db),
) -> ProvisioningRuntimeConfigResponse:
    try:
        result = ProvisioningService(db).complete_claim(
            bootstrap_id=payload.bootstrap_id,
            claim_token=payload.claim_token,
            fw_version=payload.fw_version,
            protocol=payload.protocol,
            mqtt_client_id=payload.mqtt_client_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ProvisioningRuntimeConfigResponse(**result.__dict__)
