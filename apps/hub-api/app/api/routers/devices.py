from app.api.deps import get_db
from app.schemas.devices import DeviceDetailResponse, DeviceListItem, DeviceListResponse
from app.services.device_detail_service import DeviceDetailService
from app.services.device_registry_service import DeviceRegistryService
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("", response_model=DeviceListResponse)
def list_devices(db: Session = Depends(get_db)) -> DeviceListResponse:
    service = DeviceRegistryService(db)
    items = [DeviceListItem.model_validate(device) for device in service.list_devices()]
    return DeviceListResponse(items=items)


@router.get("/{device_id}", response_model=DeviceDetailResponse)
def get_device_detail(device_id: str, db: Session = Depends(get_db)) -> DeviceDetailResponse:
    detail = DeviceDetailService(db).get(device_id=device_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return detail
