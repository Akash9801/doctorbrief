from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=200)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    specialty: str | None = Field(default=None, max_length=150)
    clinic_name: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=30)
    registration_number: str | None = Field(default=None, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class DoctorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    full_name: str
    email: EmailStr
    specialty: str | None = None
    clinic_name: str | None = None
    phone: str | None = None
    registration_number: str | None = None
    created_at: datetime
    updated_at: datetime


class DoctorUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    specialty: str | None = Field(default=None, max_length=150)
    clinic_name: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=30)
    registration_number: str | None = Field(default=None, max_length=100)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    doctor: DoctorResponse
