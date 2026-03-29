from app.api.deps import get_current_user, get_db
from app.domain.user import User
from app.schemas.devices import (
    DeviceDeleteResponse,
    DeviceDetailResponse,
    DeviceListItem,
    DeviceListResponse,
    DeviceUpdateRequest,
)
from app.services.device_detail_service import DeviceDetailService
from app.services.device_removal_service import DeviceRemovalService
from app.services.device_registry_service import DeviceRegistryService
from app.services.device_update_service import DeviceUpdateService
from app.services.room_service import RoomService
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("", response_model=DeviceListResponse)
def list_devices(db: Session = Depends(get_db)) -> DeviceListResponse:
    device_service = DeviceRegistryService(db)
    room_map = {room.id: room.name for room in RoomService(db).list_rooms()}
    items = [
        DeviceListItem(
            id=device.id,
            site_id=device.site_id,
            room_id=device.room_id,
            room_name=room_map.get(device.room_id) if device.room_id else None,
            name=device.name,
            model=device.model,
            device_type=device.device_type,
            protocol=device.protocol,
            status=device.status,
            provisioning_status=device.provisioning_status,
            fw_version=device.fw_version,
            mqtt_client_id=device.mqtt_client_id,
            last_seen_at=device.last_seen_at,
        )
        for device in device_service.list_devices()
    ]
    return DeviceListResponse(items=items)


@router.get("/{device_id}", response_model=DeviceDetailResponse)
def get_device_detail(device_id: str, db: Session = Depends(get_db)) -> DeviceDetailResponse:
    detail = DeviceDetailService(db).get(device_id=device_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return detail


@router.patch("/{device_id}", response_model=DeviceListItem)
def update_device(
    device_id: str,
    payload: DeviceUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DeviceListItem:
    room_service = RoomService(db)
    try:
        device = DeviceUpdateService(db).update_metadata(
            device_id=device_id,
            name=payload.name,
            room_id=payload.room_id,
            actor_id=current_user.id,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if detail in {"Device not found", "Room not found"} else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=detail) from exc
    room = room_service.repo.get_by_id(device.room_id) if device.room_id else None
    return DeviceListItem(
        id=device.id,
        site_id=device.site_id,
        room_id=device.room_id,
        room_name=room.name if room is not None else None,
        name=device.name,
        model=device.model,
        device_type=device.device_type,
        protocol=device.protocol,
        status=device.status,
        provisioning_status=device.provisioning_status,
        fw_version=device.fw_version,
        mqtt_client_id=device.mqtt_client_id,
        last_seen_at=device.last_seen_at,
    )


@router.delete("/{device_id}", response_model=DeviceDeleteResponse)
def delete_device(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DeviceDeleteResponse:
    try:
        removed_device_id = DeviceRemovalService(db).remove(device_id=device_id, actor=current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return DeviceDeleteResponse(device_id=removed_device_id, removed=True)
