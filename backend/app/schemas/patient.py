from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator


class PatientCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=200)
    date_of_birth: date | None = None
    age: int | None = Field(default=None, ge=0, le=130)
    gender: str = Field(..., min_length=1, max_length=32)
    phone: str = Field(..., min_length=7, max_length=30)
    medical_history: str | None = Field(default=None, max_length=4000)
    allergies: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_age_or_dob(self):
        if self.date_of_birth is None and self.age is None:
            raise ValueError("Either date_of_birth or age must be provided.")
        return self


class PatientUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    date_of_birth: date | None = None
    age: int | None = Field(default=None, ge=0, le=130)
    gender: str | None = Field(default=None, min_length=1, max_length=32)
    phone: str | None = Field(default=None, min_length=7, max_length=30)
    medical_history: str | None = Field(default=None, max_length=4000)
    allergies: str | None = Field(default=None, max_length=2000)


class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    doctor_id: str
    patient_code: str
    full_name: str
    date_of_birth: date | None = None
    age: int | None = None
    gender: str
    phone: str
    medical_history: str | None = None
    allergies: str | None = None
    created_at: datetime
    updated_at: datetime
    consultation_count: int = 0
