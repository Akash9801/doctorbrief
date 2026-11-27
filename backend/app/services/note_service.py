from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.clinical_note import ClinicalNote
from app.models.consultation import Consultation
from app.schemas.note import (
    ClinicalNoteAmendRequest,
    ClinicalNoteResponse,
    ClinicalNoteUpdateRequest,
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_owned_note(db: Session, doctor_id: str, note_id: str) -> ClinicalNote:
    note = (
        db.query(ClinicalNote)
        .options(joinedload(ClinicalNote.consultation))
        .filter(ClinicalNote.id == note_id)
        .first()
    )
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinical note not found.")
    if note.consultation.doctor_id != doctor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this clinical note.",
        )
    return note


def get_latest_note_for_consultation(
    db: Session,
    doctor_id: str,
    consultation_id: str,
) -> ClinicalNoteResponse:
    consultation = db.query(Consultation).filter(Consultation.id == consultation_id).first()
    if consultation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation not found.")
    if consultation.doctor_id != doctor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this consultation.",
        )
    note = (
        db.query(ClinicalNote)
        .filter(ClinicalNote.consultation_id == consultation_id)
        .order_by(ClinicalNote.version.desc())
        .first()
    )
    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No clinical note has been generated for this consultation yet.",
        )
    return ClinicalNoteResponse.model_validate(note)


def update_clinical_note(
    db: Session,
    doctor_id: str,
    note_id: str,
    payload: ClinicalNoteUpdateRequest,
) -> ClinicalNoteResponse:
    note = get_owned_note(db, doctor_id, note_id)
    if note.status == "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Approved clinical notes cannot be modified directly. Create an amendment version instead.",
        )

    data = payload.model_dump(exclude_unset=True)
    for field in ("subjective", "objective", "assessment", "plan"):
        if field in data and data[field] is not None:
            setattr(note, field, data[field].strip())

    if "status" in data and data["status"] is not None:
        note.status = data["status"]
    elif note.status == "DRAFT":
        note.status = "UNDER_REVIEW"

    db.commit()
    db.refresh(note)
    return ClinicalNoteResponse.model_validate(note)


def approve_clinical_note(
    db: Session,
    doctor_id: str,
    note_id: str,
    confirm_accuracy: bool,
) -> ClinicalNoteResponse:
    if not confirm_accuracy:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Doctor confirmation of clinical accuracy is required to approve a note.",
        )

    note = get_owned_note(db, doctor_id, note_id)
    if note.status == "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This clinical note version is already approved.",
        )

    if not any([note.subjective.strip(), note.objective.strip(), note.assessment.strip(), note.plan.strip()]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot approve an empty clinical note.",
        )

    now = utcnow()
    note.status = "APPROVED"
    note.approved_by = doctor_id
    note.approved_at = now

    consultation = note.consultation
    consultation.status = "COMPLETED"
    if consultation.ended_at is None:
        consultation.ended_at = now

    db.commit()
    db.refresh(note)
    return ClinicalNoteResponse.model_validate(note)


def amend_approved_note(
    db: Session,
    doctor_id: str,
    note_id: str,
    payload: ClinicalNoteAmendRequest,
) -> ClinicalNoteResponse:
    note = get_owned_note(db, doctor_id, note_id)
    if note.status != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only approved notes require an amendment version. Edit draft notes directly.",
        )

    max_version = (
        db.query(func.max(ClinicalNote.version))
        .filter(ClinicalNote.consultation_id == note.consultation_id)
        .scalar()
        or note.version
    )

    amended = ClinicalNote(
        consultation_id=note.consultation_id,
        version=max_version + 1,
        subjective=payload.subjective.strip(),
        objective=payload.objective.strip(),
        assessment=payload.assessment.strip(),
        plan=payload.plan.strip(),
        status="DRAFT",
        amendment_reason=payload.amendment_reason.strip(),
        parent_note_id=note.id,
        is_mock=note.is_mock,
    )
    db.add(amended)
    db.commit()
    db.refresh(amended)
    return ClinicalNoteResponse.model_validate(amended)
