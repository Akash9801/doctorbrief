from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class SoapNoteDraft(BaseModel):
    subjective: str = Field(..., description="Subjective section grounded in patient-reported info.")
    objective: str = Field(..., description="Objective section grounded in explicitly stated vitals/exam findings.")
    assessment: str = Field(..., description="Assessment section grounded in doctor-stated assessment.")
    plan: str = Field(..., description="Plan section grounded in doctor-stated plan/follow-up.")


class ClinicalNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    consultation_id: str
    version: int
    subjective: str
    objective: str
    assessment: str
    plan: str
    status: Literal["DRAFT", "UNDER_REVIEW", "APPROVED"]
    amendment_reason: str | None = None
    parent_note_id: str | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    is_mock: bool = False
    created_at: datetime
    updated_at: datetime


class ClinicalNoteUpdateRequest(BaseModel):
    subjective: str | None = Field(default=None, max_length=20000)
    objective: str | None = Field(default=None, max_length=20000)
    assessment: str | None = Field(default=None, max_length=20000)
    plan: str | None = Field(default=None, max_length=20000)
    status: Literal["DRAFT", "UNDER_REVIEW"] | None = None


class ClinicalNoteAmendRequest(BaseModel):
    subjective: str = Field(..., min_length=1, max_length=20000)
    objective: str = Field(..., min_length=1, max_length=20000)
    assessment: str = Field(..., min_length=1, max_length=20000)
    plan: str = Field(..., min_length=1, max_length=20000)
    amendment_reason: str = Field(..., min_length=3, max_length=1000)


class ClinicalNoteApproveRequest(BaseModel):
    confirm_accuracy: bool = True
