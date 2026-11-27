import asyncio
import logging
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload
from starlette.concurrency import run_in_threadpool

from app.ai.client import (
    AIServiceError,
    extract_clinical_information,
    generate_soap_note_draft,
    transcribe_audio_bytes,
)
from app.config import get_settings
from app.models.clinical_extraction import ClinicalExtraction
from app.models.clinical_note import ClinicalNote
from app.models.consultation import Consultation
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.transcript import Transcript
from app.schemas.consultation import (
    ConsultationCreate,
    ConsultationDetailResponse,
    ConsultationSummary,
    ConsultationUpdate,
)
from app.schemas.extraction import ClinicalExtractionPayload, ClinicalExtractionResponse
from app.schemas.note import ClinicalNoteResponse
from app.schemas.transcript import TranscriptResponse, TranscriptUpdateRequest
from app.services.patient_service import get_owned_patient, to_patient_response

logger = logging.getLogger("doctorbrief.consultation")

ALLOWED_AUDIO_EXTENSIONS = {".webm", ".wav", ".mp3", ".m4a", ".ogg", ".oga", ".mp4", ".mpeg", ".mpga", ".flac"}
ALLOWED_AUDIO_CONTENT_TYPES = {
    "audio/webm",
    "video/webm",
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
    "audio/ogg",
    "application/ogg",
    "audio/oga",
    "audio/flac",
    "audio/x-flac",
    "audio/aac",
}


def _commit_with_rollback(db: Session, context: str) -> None:
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Database transaction failed during %s", context)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="A database error occurred while saving consultation data. Please retry.",
        ) from exc


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_owned_consultation(db: Session, doctor_id: str, consultation_id: str) -> Consultation:
    consultation = (
        db.query(Consultation)
        .options(
            joinedload(Consultation.patient),
            joinedload(Consultation.doctor),
            joinedload(Consultation.transcript),
            joinedload(Consultation.extraction),
            joinedload(Consultation.notes),
        )
        .filter(Consultation.id == consultation_id)
        .first()
    )
    if consultation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation not found.")
    if consultation.doctor_id != doctor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this consultation.",
        )
    return consultation


def to_consultation_detail(db: Session, consultation: Consultation) -> ConsultationDetailResponse:
    notes_sorted = sorted(consultation.notes, key=lambda n: n.version, reverse=True)
    latest_note = ClinicalNoteResponse.model_validate(notes_sorted[0]) if notes_sorted else None
    return ConsultationDetailResponse(
        id=consultation.id,
        doctor_id=consultation.doctor_id,
        patient_id=consultation.patient_id,
        started_at=consultation.started_at,
        ended_at=consultation.ended_at,
        status=consultation.status,
        consent_status=consultation.consent_status,
        consent_confirmed_at=consultation.consent_confirmed_at,
        audio_filename=consultation.audio_filename,
        audio_duration_seconds=consultation.audio_duration_seconds,
        created_at=consultation.created_at,
        updated_at=consultation.updated_at,
        patient=to_patient_response(db, consultation.patient),
        doctor_name=consultation.doctor.full_name,
        transcript=TranscriptResponse.model_validate(consultation.transcript)
        if consultation.transcript
        else None,
        extraction=ClinicalExtractionResponse.model_validate(consultation.extraction)
        if consultation.extraction
        else None,
        latest_note=latest_note,
        note_versions=[ClinicalNoteResponse.model_validate(n) for n in notes_sorted],
    )


def create_consultation(db: Session, doctor: Doctor, payload: ConsultationCreate) -> ConsultationDetailResponse:
    patient = get_owned_patient(db, doctor.id, payload.patient_id)
    now = utcnow()
    consultation = Consultation(
        doctor_id=doctor.id,
        patient_id=patient.id,
        started_at=now,
        status="IN_PROGRESS",
        consent_status=payload.consent_status,
        consent_confirmed_at=now if payload.consent_status == "GRANTED" else None,
    )
    db.add(consultation)
    db.commit()
    db.refresh(consultation)
    loaded = get_owned_consultation(db, doctor.id, consultation.id)
    return to_consultation_detail(db, loaded)


def list_consultations(
    db: Session,
    doctor_id: str,
    search: str | None = None,
    patient_id: str | None = None,
    status_filter: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[ConsultationSummary]:
    query = (
        db.query(Consultation)
        .join(Patient, Consultation.patient_id == Patient.id)
        .join(Doctor, Consultation.doctor_id == Doctor.id)
        .options(
            joinedload(Consultation.patient),
            joinedload(Consultation.doctor),
            joinedload(Consultation.transcript),
            joinedload(Consultation.notes),
        )
        .filter(Consultation.doctor_id == doctor_id)
    )

    if patient_id:
        query = query.filter(Consultation.patient_id == patient_id)
    if status_filter and status_filter.lower() != "all":
        query = query.filter(Consultation.status == status_filter.upper())
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Patient.full_name.ilike(term),
                Patient.patient_code.ilike(term),
            )
        )
    if date_from:
        try:
            start_dt = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)
            query = query.filter(Consultation.started_at >= start_dt)
        except ValueError:
            pass
    if date_to:
        try:
            end_dt = datetime.fromisoformat(date_to).replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc
            )
            query = query.filter(Consultation.started_at <= end_dt)
        except ValueError:
            pass

    rows = query.order_by(Consultation.started_at.desc()).all()
    summaries: list[ConsultationSummary] = []
    for c in rows:
        notes_sorted = sorted(c.notes, key=lambda n: n.version, reverse=True)
        note_status = notes_sorted[0].status if notes_sorted else "NONE"
        summaries.append(
            ConsultationSummary(
                id=c.id,
                doctor_id=c.doctor_id,
                patient_id=c.patient_id,
                patient_name=c.patient.full_name,
                patient_code=c.patient.patient_code,
                doctor_name=c.doctor.full_name,
                started_at=c.started_at,
                ended_at=c.ended_at,
                status=c.status,
                consent_status=c.consent_status,
                transcription_status=c.transcript.processing_status if c.transcript else "NONE",
                note_status=note_status,
                audio_duration_seconds=c.audio_duration_seconds,
                created_at=c.created_at,
            )
        )
    return summaries


def update_consultation(
    db: Session,
    doctor_id: str,
    consultation_id: str,
    payload: ConsultationUpdate,
) -> ConsultationDetailResponse:
    consultation = get_owned_consultation(db, doctor_id, consultation_id)
    if payload.consent_status is not None:
        consultation.consent_status = payload.consent_status
        if payload.consent_status == "GRANTED" and consultation.consent_confirmed_at is None:
            consultation.consent_confirmed_at = utcnow()
    if payload.status is not None:
        consultation.status = payload.status
    if payload.ended_at is not None:
        consultation.ended_at = payload.ended_at
    if payload.audio_duration_seconds is not None:
        consultation.audio_duration_seconds = payload.audio_duration_seconds
    db.commit()
    loaded = get_owned_consultation(db, doctor_id, consultation_id)
    return to_consultation_detail(db, loaded)


def validate_audio_upload(filename: str, content_type: str | None, audio_bytes: bytes, max_bytes: int) -> None:
    if not audio_bytes or len(audio_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio file is empty. Please record audio before uploading.",
        )
    if len(audio_bytes) > max_bytes:
        max_mb = max_bytes // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Audio file exceeds the maximum allowed size of {max_mb} MB.",
        )
    lower_name = (filename or "").lower()
    ext_ok = any(lower_name.endswith(ext) for ext in ALLOWED_AUDIO_EXTENSIONS)
    normalized_ct = (content_type or "").split(";")[0].strip().lower()
    ct_ok = normalized_ct in ALLOWED_AUDIO_CONTENT_TYPES if normalized_ct else False
    if not ext_ok and not ct_ok:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported audio format. Please upload WebM, WAV, MP3, M4A, or OGG audio.",
        )


async def process_transcription(
    db: Session,
    doctor_id: str,
    consultation_id: str,
    filename: str,
    content_type: str | None,
    audio_bytes: bytes,
    max_bytes: int,
    duration_seconds: int | None = None,
) -> TranscriptResponse:
    consultation = get_owned_consultation(db, doctor_id, consultation_id)
    if consultation.consent_status != "GRANTED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient consent must be confirmed before uploading or transcribing audio.",
        )

    validate_audio_upload(filename, content_type, audio_bytes, max_bytes)

    transcript = consultation.transcript
    if transcript is None:
        transcript = Transcript(
            consultation_id=consultation.id,
            original_text="",
            processing_status="PENDING",
        )
        db.add(transcript)
        try:
            db.flush()
        except SQLAlchemyError as exc:
            db.rollback()
            logger.exception("Database error initializing transcript record")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="A database error occurred while preparing transcription.",
            ) from exc

    consultation.audio_filename = filename
    if duration_seconds is not None:
        consultation.audio_duration_seconds = duration_seconds

    settings = get_settings()
    try:
        result = await asyncio.wait_for(
            run_in_threadpool(transcribe_audio_bytes, audio_bytes, filename, content_type),
            timeout=settings.WHISPER_TIMEOUT_SECONDS,
        )
    except (asyncio.TimeoutError, TimeoutError) as exc:
        logger.warning("Local Whisper transcription timed out after %ss", settings.WHISPER_TIMEOUT_SECONDS)
        transcript.processing_status = "FAILED"
        transcript.error_message = "Transcription timed out. Please try a shorter recording."
        _commit_with_rollback(db, "transcription timeout status update")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Audio transcription timed out. Please try a shorter recording.",
        ) from exc
    except AIServiceError as exc:
        transcript.processing_status = "FAILED"
        transcript.error_message = exc.message
        _commit_with_rollback(db, "transcription failure status update")
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    transcript.original_text = result.text
    transcript.edited_text = result.text
    transcript.language = result.language
    transcript.processing_status = "COMPLETED"
    transcript.error_message = None
    transcript.is_mock = result.is_mock

    if consultation.status == "IN_PROGRESS":
        consultation.status = "TRANSCRIBED"
    if consultation.ended_at is None:
        consultation.ended_at = utcnow()

    _commit_with_rollback(db, "saving completed transcript")
    db.refresh(transcript)
    return TranscriptResponse.model_validate(transcript)


def update_transcript_text(
    db: Session,
    doctor_id: str,
    consultation_id: str,
    payload: TranscriptUpdateRequest,
) -> TranscriptResponse:
    consultation = get_owned_consultation(db, doctor_id, consultation_id)
    if consultation.transcript is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No transcript found for this consultation.",
        )
    consultation.transcript.edited_text = payload.edited_text.strip()
    if payload.language is not None:
        consultation.transcript.language = payload.language.strip()
    _commit_with_rollback(db, "updating transcript text")
    db.refresh(consultation.transcript)
    return TranscriptResponse.model_validate(consultation.transcript)


def run_clinical_extraction(
    db: Session,
    doctor_id: str,
    consultation_id: str,
) -> ClinicalExtractionResponse:
    consultation = get_owned_consultation(db, doctor_id, consultation_id)
    if consultation.transcript is None or not (
        consultation.transcript.edited_text or consultation.transcript.original_text
    ).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A completed transcript is required before extracting clinical information.",
        )

    text_to_analyze = (
        consultation.transcript.edited_text or consultation.transcript.original_text
    ).strip()

    try:
        result = extract_clinical_information(text_to_analyze)
    except AIServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    extraction = consultation.extraction
    if extraction is None:
        extraction = ClinicalExtraction(
            consultation_id=consultation.id,
            extracted_data=result.payload.model_dump(),
            missing_information=result.payload.missing_information,
            model_name=result.model_name,
            is_mock=result.is_mock,
        )
        db.add(extraction)
    else:
        extraction.extracted_data = result.payload.model_dump()
        extraction.missing_information = result.payload.missing_information
        extraction.model_name = result.model_name
        extraction.is_mock = result.is_mock

    if consultation.status in {"IN_PROGRESS", "TRANSCRIBED"}:
        consultation.status = "EXTRACTED"

    _commit_with_rollback(db, "saving clinical extraction")
    db.refresh(extraction)
    return ClinicalExtractionResponse.model_validate(extraction)


def generate_soap_for_consultation(
    db: Session,
    doctor_id: str,
    consultation_id: str,
) -> ClinicalNoteResponse:
    consultation = get_owned_consultation(db, doctor_id, consultation_id)
    if consultation.transcript is None or not (
        consultation.transcript.edited_text or consultation.transcript.original_text
    ).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A transcript is required before generating a SOAP note.",
        )

    transcript_text = (
        consultation.transcript.edited_text or consultation.transcript.original_text
    ).strip()

    if consultation.extraction is None:
        extraction_resp = run_clinical_extraction(db, doctor_id, consultation_id)
        extracted_payload = ClinicalExtractionPayload.model_validate(extraction_resp.extracted_data)
        consultation = get_owned_consultation(db, doctor_id, consultation_id)
    else:
        extracted_payload = ClinicalExtractionPayload.model_validate(
            consultation.extraction.extracted_data
        )

    try:
        soap_result = generate_soap_note_draft(transcript_text, extracted_payload)
    except AIServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    existing_versions = [n.version for n in consultation.notes]
    next_version = (max(existing_versions) + 1) if existing_versions else 1

    # Never overwrite an already approved note; create a new DRAFT version
    note = ClinicalNote(
        consultation_id=consultation.id,
        version=next_version,
        subjective=soap_result.draft.subjective,
        objective=soap_result.draft.objective,
        assessment=soap_result.draft.assessment,
        plan=soap_result.draft.plan,
        status="DRAFT",
        is_mock=soap_result.is_mock,
    )
    db.add(note)
    _commit_with_rollback(db, "saving generated SOAP note")
    db.refresh(note)
    return ClinicalNoteResponse.model_validate(note)
