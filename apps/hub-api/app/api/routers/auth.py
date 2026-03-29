from app.api.deps import get_current_user, get_db
from app.domain.user import User
from app.schemas.auth import LoginRequest, LoginResponse, MeResponse
from app.services.auth_service import AuthService
from app.services.hub_setup_service import HubSetupService
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    if HubSetupService(db).get_status().requires_onboarding:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Hub onboarding is required before anyone can sign in.",
        )
    result = AuthService(db).authenticate(email=payload.email, password=payload.password)
    if result is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token, user = result
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        display_name=user.display_name,
    )


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user)) -> MeResponse:
    return MeResponse.model_validate(current_user)
