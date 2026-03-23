from app.api.deps import get_app_settings
from app.schemas.system import HealthResponse
from fastapi import APIRouter, Depends

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(settings=Depends(get_app_settings)) -> HealthResponse:
    return HealthResponse(status="ok", service=settings.app_name, environment=settings.environment)
