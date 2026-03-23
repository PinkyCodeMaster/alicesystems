from pydantic import BaseModel, ConfigDict, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    display_name: str


class MeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    site_id: str
    email: str
    display_name: str
    role: str
    is_active: int
