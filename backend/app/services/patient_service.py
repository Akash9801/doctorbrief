from datetime import date
from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.consultation import Consultation
from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientResponse, PatientUpdate


def _generate_patient_code(db: Session, doctor_id: str) -> str:
    codes = (
        db.query(Patient.patient_code)
        .filter(Patient.doctor_id == doctor_id)
        .all()
    )
    max_num = 0
    for (code,) in codes:
        if code and code.startswith("DB-"):
            try:
                max_num = max(max_num, int(code.split("-", 1)[1]))
            except ValueError:
                continue
    return f"DB-{max_num + 1:04d}"


def _derive_age(dob: date | None, explicit_age: int | None) -> int | None:
    if explicit_age is not None:
        return explicit_age
    if dob is None:
        return None
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def to_patient_response(db: Session, patient: Patient) -> PatientResponse:
    count = (
        db.query(func.count(Consultation.id))
        .filter(Consultation.patient_id == patient.id)
        .scalar()
        or 0
    )
    return PatientResponse(
        id=patient.id,
        doctor_id=patient.doctor_id,
        patient_code=patient.patient_code,
        full_name=patient.full_name,
        date_of_birth=patient.date_of_birth,
        age=patient.age,
        gender=patient.gender,
        phone=patient.phone,
        medical_history=patient.medical_history,
        allergies=patient.allergies,
        created_at=patient.created_at,
        updated_at=patient.updated_at,
        consultation_count=count,
    )


def get_owned_patient(db: Session, doctor_id: str, patient_id: str) -> Patient:
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
    if patient.doctor_id != doctor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this patient record.",
        )
    return patient


def list_patients(
    db: Session,
    doctor_id: str,
    search: str | None = None,
    gender: str | None = None,
) -> list[PatientResponse]:
    query = db.query(Patient).filter(Patient.doctor_id == doctor_id)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Patient.full_name.ilike(term),
                Patient.patient_code.ilike(term),
                Patient.phone.ilike(term),
            )
        )
    if gender and gender.lower() != "all":
        query = query.filter(func.lower(Patient.gender) == gender.lower())

    patients = query.order_by(Patient.created_at.desc()).all()
    if not patients:
        return []

    counts_rows = (
        db.query(Consultation.patient_id, func.count(Consultation.id))
        .filter(Consultation.doctor_id == doctor_id)
        .group_by(Consultation.patient_id)
        .all()
    )
    counts_map = {pid: cnt for pid, cnt in counts_rows}

    return [
        PatientResponse(
            id=p.id,
            doctor_id=p.doctor_id,
            patient_code=p.patient_code,
            full_name=p.full_name,
            date_of_birth=p.date_of_birth,
            age=p.age,
            gender=p.gender,
            phone=p.phone,
            medical_history=p.medical_history,
            allergies=p.allergies,
            created_at=p.created_at,
            updated_at=p.updated_at,
            consultation_count=counts_map.get(p.id, 0),
        )
        for p in patients
    ]


def create_patient(db: Session, doctor_id: str, payload: PatientCreate) -> PatientResponse:
    patient = Patient(
        doctor_id=doctor_id,
        patient_code=_generate_patient_code(db, doctor_id),
        full_name=payload.full_name.strip(),
        date_of_birth=payload.date_of_birth,
        age=_derive_age(payload.date_of_birth, payload.age),
        gender=payload.gender.strip(),
        phone=payload.phone.strip(),
        medical_history=payload.medical_history.strip() if payload.medical_history else None,
        allergies=payload.allergies.strip() if payload.allergies else None,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return to_patient_response(db, patient)


def update_patient(
    db: Session,
    doctor_id: str,
    patient_id: str,
    payload: PatientUpdate,
) -> PatientResponse:
    patient = get_owned_patient(db, doctor_id, patient_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        if isinstance(value, str):
            value = value.strip()
        setattr(patient, field, value)
    if "date_of_birth" in data and "age" not in data and patient.date_of_birth is not None:
        patient.age = _derive_age(patient.date_of_birth, None)
    db.commit()
    db.refresh(patient)
    return to_patient_response(db, patient)


def delete_patient(db: Session, doctor_id: str, patient_id: str) -> None:
    patient = get_owned_patient(db, doctor_id, patient_id)
    db.delete(patient)
    db.commit()
