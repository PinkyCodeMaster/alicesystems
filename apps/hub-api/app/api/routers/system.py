from app.api.deps import get_current_actor, get_db
from app.schemas.system import (
    AutoLightSettingsResponse,
    AutoLightSettingsUpdateRequest,
    HubSetupRequest,
    HubSetupResponse,
    HubSetupStatusResponse,
    RootResponse,
    StackHealthResponse,
)
from app.services.auto_light_settings_service import AutoLightSettingsService
from app.services.hub_setup_service import HubSetupService
from app.services.site_service import SiteService
from app.services.stack_health_service import StackHealthService
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/", response_model=RootResponse)
def root(db: Session = Depends(get_db)) -> RootResponse:
    service = SiteService(db)
    site = service.get_or_create_default_site()
    setup_status = HubSetupService(db).get_status()
    return RootResponse(
        service="Alice Home OS API",
        version="0.1.0",
        site_id=site.id,
        site_name=site.name,
        setup_completed=setup_status.setup_completed,
        requires_onboarding=setup_status.requires_onboarding,
    )


@router.get("/system/setup-status", response_model=HubSetupStatusResponse)
def get_setup_status(db: Session = Depends(get_db)) -> HubSetupStatusResponse:
    return HubSetupStatusResponse(**HubSetupService(db).get_status().__dict__)


@router.post("/system/setup", response_model=HubSetupResponse)
def complete_hub_setup(
    payload: HubSetupRequest,
    db: Session = Depends(get_db),
) -> HubSetupResponse:
    try:
        result = HubSetupService(db).complete_setup(
            site_name=payload.site_name,
            timezone=payload.timezone,
            owner_email=payload.owner_email,
            owner_display_name=payload.owner_display_name,
            password=payload.password,
            room_names=payload.room_names,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return HubSetupResponse(**result.__dict__)


@router.get("/system/auto-light", response_model=AutoLightSettingsResponse)
def get_auto_light_settings(
    db: Session = Depends(get_db),
    _current_actor=Depends(get_current_actor),
) -> AutoLightSettingsResponse:
    settings = AutoLightSettingsService(db).get()
    return AutoLightSettingsResponse(**settings.__dict__)


@router.put("/system/auto-light", response_model=AutoLightSettingsResponse)
def put_auto_light_settings(
    payload: AutoLightSettingsUpdateRequest,
    db: Session = Depends(get_db),
    _current_actor=Depends(get_current_actor),
) -> AutoLightSettingsResponse:
    settings = AutoLightSettingsService(db).save(
        enabled=payload.enabled,
        sensor_entity_id=payload.sensor_entity_id,
        target_entity_id=payload.target_entity_id,
        motion_entity_id=payload.motion_entity_id,
        mode=payload.mode,
        on_lux=payload.on_lux,
        off_lux=payload.off_lux,
        on_raw=payload.on_raw,
        off_raw=payload.off_raw,
        block_on_during_daytime=payload.block_on_during_daytime,
        daytime_start_hour=payload.daytime_start_hour,
        daytime_end_hour=payload.daytime_end_hour,
        allow_daytime_turn_on_when_very_dark=payload.allow_daytime_turn_on_when_very_dark,
        daytime_on_lux=payload.daytime_on_lux,
        daytime_on_raw=payload.daytime_on_raw,
        require_motion_for_turn_on=payload.require_motion_for_turn_on,
        motion_hold_seconds=payload.motion_hold_seconds,
    )
    return AutoLightSettingsResponse(**settings.__dict__)


@router.get("/system/stack-health", response_model=StackHealthResponse)
def get_stack_health(
    db: Session = Depends(get_db),
    _current_actor=Depends(get_current_actor),
) -> StackHealthResponse:
    return StackHealthService(db).get()
