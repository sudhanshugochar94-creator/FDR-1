from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class InstitutionBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=500)
    code: str = Field(..., min_length=2, max_length=50)
    address: Optional[str] = Field(None, max_length=1000)
    city: Optional[str] = Field(None, max_length=200)
    state: Optional[str] = Field(None, max_length=200)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, max_length=20)
    is_active: bool = True


class InstitutionCreate(InstitutionBase):
    pass


class InstitutionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=500)
    code: Optional[str] = Field(None, min_length=2, max_length=50)
    address: Optional[str] = Field(None, max_length=1000)
    city: Optional[str] = Field(None, max_length=200)
    state: Optional[str] = Field(None, max_length=200)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None


class InstitutionResponse(InstitutionBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InstitutionBriefResponse(BaseModel):
    id: UUID
    name: str
    code: str

    model_config = ConfigDict(from_attributes=True)
