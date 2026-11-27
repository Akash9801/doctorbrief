from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.session import get_db
from app.models.doctor import Doctor
from app.schemas.consultation import (
    ConsultationCreate,
    ConsultationDetailResponse,
    ConsultationSummary,
    ConsultationUpdate,
)
from app.schemas.extraction import ClinicalExtractionResponse
from app.schemas.note import ClinicalNoteResponse
from app.schemas.transcript import TranscriptResponse, TranscriptUpdateRequest
from app.security.dependencies import get_current_doctor
from app.services import consultation_service, note_service

router = APIRouter(prefix="/api/consultations", tags=["Consultations"])


@router.get("", response_model=list[ConsultationSummary])
def list_consultations(
    search: str | None = Query(default=None),
    patient_id: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    return consultation_service.list_consultations(
        db,
        current_doctor.id,
        search=search,
        patient_id=patient_id,
        status_filter=status_filter,
        date_from=date_from,
        date_to=date_to,
    )


@router.post("", response_model=ConsultationDetailResponse, status_code=status.HTTP_201_CREATED)
def create_consultation(
    payload: ConsultationCreate,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    return consultation_service.create_consultation(db, current_doctor, payload)


@router.get("/{consultation_id}", response_model=ConsultationDetailResponse)
def get_consultation(
    consultation_id: str,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    consultation = consultation_service.get_owned_consultation(db, current_doctor.id, consultation_id)
    return consultation_service.to_consultation_detail(db, consultation)


@router.patch("/{consultation_id}", response_model=ConsultationDetailResponse)
def update_consultation(
    consultation_id: str,
    payload: ConsultationUpdate,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    return consultation_service.update_consultation(db, current_doctor.id, consultation_id, payload)


@router.post("/{consultation_id}/transcribe", response_model=TranscriptResponse)
async def transcribe_consultation_audio(
    consultation_id: str,
    file: UploadFile = File(...),
    duration_seconds: int | None = Form(default=None),
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    audio_bytes = await file.read()
    return consultation_service.process_transcription(
        db=db,
        doctor_id=current_doctor.id,
        consultation_id=consultation_id,
        filename=file.filename or "recording.webm",
        content_type=file.content_type,
        audio_bytes=audio_bytes,
        max_bytes=settings.max_audio_size_bytes,
        duration_seconds=duration_seconds,
    )


@router.patch("/{consultation_id}/transcript", response_model=TranscriptResponse)
def update_transcript(
    consultation_id: str,
    payload: TranscriptUpdateRequest,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    return consultation_service.update_transcript_text(
        db, current_doctor.id, consultation_id, payload
    )


@router.post("/{consultation_id}/extract", response_model=ClinicalExtractionResponse)
def extract_clinical_info(
    consultation_id: str,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    return consultation_service.run_clinical_extraction(db, current_doctor.id, consultation_id)


@router.post("/{consultation_id}/generate-note", response_model=ClinicalNoteResponse)
def generate_clinical_note(
    consultation_id: str,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    return consultation_service.generate_soap_for_consultation(
        db, current_doctor.id, consultation_id
    )


@router.get("/{consultation_id}/note", response_model=ClinicalNoteResponse)
def get_consultation_note(
    consultation_id: str,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    return note_service.get_latest_note_for_consultation(db, current_doctor.id, consultation_id)
