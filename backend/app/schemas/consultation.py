from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.extraction import ClinicalExtractionResponse
from app.schemas.note import ClinicalNoteResponse
from app.schemas.patient import PatientResponse
from app.schemas.transcript import TranscriptResponse


class ConsultationCreate(BaseModel):
    patient_id: str
    consent_status: Literal["PENDING", "GRANTED"] = "PENDING"


class ConsultationUpdate(BaseModel):
    status: Literal["IN_PROGRESS", "TRANSCRIBED", "EXTRACTED", "COMPLETED"] | None = None
    consent_status: Literal["PENDING", "GRANTED"] | None = None
    ended_at: datetime | None = None
    audio_duration_seconds: int | None = Field(default=None, ge=0, le=86400)


class ConsultationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    doctor_id: str
    patient_id: str
    patient_name: str
    patient_code: str
    doctor_name: str
    started_at: datetime
    ended_at: datetime | None = None
    status: str
    consent_status: str
    transcription_status: str | None = None
    note_status: str | None = None
    audio_duration_seconds: int | None = None
    created_at: datetime


class ConsultationDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    doctor_id: str
    patient_id: str
    started_at: datetime
    ended_at: datetime | None = None
    status: str
    consent_status: str
    consent_confirmed_at: datetime | None = None
    audio_filename: str | None = None
    audio_duration_seconds: int | None = None
    created_at: datetime
    updated_at: datetime
    patient: PatientResponse
    doctor_name: str
    transcript: TranscriptResponse | None = None
    extraction: ClinicalExtractionResponse | None = None
    latest_note: ClinicalNoteResponse | None = None
    note_versions: list[ClinicalNoteResponse] = Field(default_factory=list)
