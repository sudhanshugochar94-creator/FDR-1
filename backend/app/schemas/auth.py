from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr
from app.models.user import UserRole
from app.schemas.institution import InstitutionBriefResponse


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    username: str
    full_name: str
    role: UserRole
    is_active: bool
    institution: Optional[InstitutionBriefResponse] = None

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None
    user: UserResponse
