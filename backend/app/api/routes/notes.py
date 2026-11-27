from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.doctor import Doctor
from app.schemas.note import (
    ClinicalNoteAmendRequest,
    ClinicalNoteApproveRequest,
    ClinicalNoteResponse,
    ClinicalNoteUpdateRequest,
)
from app.security.dependencies import get_current_doctor
from app.services import note_service

router = APIRouter(prefix="/api/notes", tags=["Clinical Notes"])


@router.patch("/{note_id}", response_model=ClinicalNoteResponse)
def update_note(
    note_id: str,
    payload: ClinicalNoteUpdateRequest,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    return note_service.update_clinical_note(db, current_doctor.id, note_id, payload)


@router.post("/{note_id}/approve", response_model=ClinicalNoteResponse)
def approve_note(
    note_id: str,
    payload: ClinicalNoteApproveRequest = Body(default=ClinicalNoteApproveRequest()),
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    return note_service.approve_clinical_note(
        db, current_doctor.id, note_id, payload.confirm_accuracy
    )


@router.post("/{note_id}/amend", response_model=ClinicalNoteResponse)
def amend_note(
    note_id: str,
    payload: ClinicalNoteAmendRequest,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    return note_service.amend_approved_note(db, current_doctor.id, note_id, payload)
