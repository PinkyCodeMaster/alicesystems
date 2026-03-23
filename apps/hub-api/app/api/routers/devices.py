from app.api.deps import get_db
from app.schemas.devices import DeviceListItem, DeviceListResponse
from app.services.device_registry_service import DeviceRegistryService
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("", response_model=DeviceListResponse)
def list_devices(db: Session = Depends(get_db)) -> DeviceListResponse:
    service = DeviceRegistryService(db)
    items = [DeviceListItem.model_validate(device) for device in service.list_devices()]
    return DeviceListResponse(items=items)
