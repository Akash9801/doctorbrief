from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session, joinedload

from app.database.session import get_db
from app.models.consultation import Consultation
from app.models.doctor import Doctor
from app.schemas.consultation import ConsultationDetailResponse
from app.schemas.patient import PatientCreate, PatientResponse, PatientUpdate
from app.security.dependencies import get_current_doctor
from app.services import consultation_service, patient_service

router = APIRouter(prefix="/api/patients", tags=["Patients"])


@router.get("", response_model=list[PatientResponse])
def list_patients(
    search: str | None = Query(default=None),
    gender: str | None = Query(default=None),
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    return patient_service.list_patients(db, current_doctor.id, search=search, gender=gender)


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: PatientCreate,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    return patient_service.create_patient(db, current_doctor.id, payload)


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(
    patient_id: str,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    patient = patient_service.get_owned_patient(db, current_doctor.id, patient_id)
    return patient_service.to_patient_response(db, patient)


@router.patch("/{patient_id}", response_model=PatientResponse)
def update_patient(
    patient_id: str,
    payload: PatientUpdate,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    return patient_service.update_patient(db, current_doctor.id, patient_id, payload)


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(
    patient_id: str,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    patient_service.delete_patient(db, current_doctor.id, patient_id)
    return None


@router.get("/{patient_id}/history", response_model=list[ConsultationDetailResponse])
def get_patient_history(
    patient_id: str,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    patient_service.get_owned_patient(db, current_doctor.id, patient_id)
    consultations = (
        db.query(Consultation)
        .options(
            joinedload(Consultation.patient),
            joinedload(Consultation.doctor),
            joinedload(Consultation.transcript),
            joinedload(Consultation.extraction),
            joinedload(Consultation.notes),
        )
        .filter(
            Consultation.doctor_id == current_doctor.id,
            Consultation.patient_id == patient_id,
        )
        .order_by(Consultation.started_at.desc())
        .all()
    )
    return [consultation_service.to_consultation_detail(db, c) for c in consultations]
