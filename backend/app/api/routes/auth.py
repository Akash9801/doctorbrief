from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.doctor import Doctor
from app.schemas.auth import (
    DoctorResponse,
    DoctorUpdateRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.security.auth import create_access_token, hash_password, verify_password
from app.security.dependencies import get_current_doctor

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_doctor(payload: RegisterRequest, db: Session = Depends(get_db)):
    normalized_email = payload.email.strip().lower()
    existing = db.query(Doctor).filter(Doctor.email == normalized_email).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        )

    doctor = Doctor(
        full_name=payload.full_name.strip(),
        email=normalized_email,
        password_hash=hash_password(payload.password),
        specialty=payload.specialty.strip() if payload.specialty else None,
        clinic_name=payload.clinic_name.strip() if payload.clinic_name else None,
        phone=payload.phone.strip() if payload.phone else None,
        registration_number=payload.registration_number.strip()
        if payload.registration_number
        else None,
    )
    db.add(doctor)
    db.commit()
    db.refresh(doctor)

    token = create_access_token(doctor.id)
    return TokenResponse(access_token=token, doctor=DoctorResponse.model_validate(doctor))


@router.post("/login", response_model=TokenResponse)
def login_doctor(payload: LoginRequest, db: Session = Depends(get_db)):
    normalized_email = payload.email.strip().lower()
    doctor = db.query(Doctor).filter(Doctor.email == normalized_email).first()
    if doctor is None or not verify_password(payload.password, doctor.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    token = create_access_token(doctor.id)
    return TokenResponse(access_token=token, doctor=DoctorResponse.model_validate(doctor))


@router.get("/me", response_model=DoctorResponse)
def get_me(current_doctor: Doctor = Depends(get_current_doctor)):
    return DoctorResponse.model_validate(current_doctor)


@router.patch("/me", response_model=DoctorResponse)
def update_me(
    payload: DoctorUpdateRequest,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        if isinstance(value, str):
            value = value.strip() or None
        setattr(current_doctor, field, value)
    db.commit()
    db.refresh(current_doctor)
    return DoctorResponse.model_validate(current_doctor)
