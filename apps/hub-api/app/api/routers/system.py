from app.api.deps import get_current_user, get_db
from app.domain.user import User
from app.schemas.system import (
    AutoLightSettingsResponse,
    AutoLightSettingsUpdateRequest,
    RootResponse,
    StackHealthResponse,
)
from app.services.auto_light_settings_service import AutoLightSettingsService
from app.services.site_service import SiteService
from app.services.stack_health_service import StackHealthService
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/", response_model=RootResponse)
def root(db: Session = Depends(get_db)) -> RootResponse:
    service = SiteService(db)
    site = service.get_or_create_default_site()
    return RootResponse(
        service="Alice Home OS API",
        version="0.1.0",
        site_id=site.id,
        site_name=site.name,
    )


@router.get("/system/auto-light", response_model=AutoLightSettingsResponse)
def get_auto_light_settings(
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> AutoLightSettingsResponse:
    settings = AutoLightSettingsService(db).get()
    return AutoLightSettingsResponse(**settings.__dict__)


@router.put("/system/auto-light", response_model=AutoLightSettingsResponse)
def put_auto_light_settings(
    payload: AutoLightSettingsUpdateRequest,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> AutoLightSettingsResponse:
    settings = AutoLightSettingsService(db).save(
        enabled=payload.enabled,
        sensor_entity_id=payload.sensor_entity_id,
        target_entity_id=payload.target_entity_id,
        mode=payload.mode,
        on_lux=payload.on_lux,
        off_lux=payload.off_lux,
        on_raw=payload.on_raw,
        off_raw=payload.off_raw,
        block_on_during_daytime=payload.block_on_during_daytime,
        daytime_start_hour=payload.daytime_start_hour,
        daytime_end_hour=payload.daytime_end_hour,
    )
    return AutoLightSettingsResponse(**settings.__dict__)


@router.get("/system/stack-health", response_model=StackHealthResponse)
def get_stack_health(
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> StackHealthResponse:
    return StackHealthService(db).get()
