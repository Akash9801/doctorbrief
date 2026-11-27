import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Consultation(Base):
    __tablename__ = "consultations"
    __table_args__ = (
        Index("ix_consultations_doctor_created", "doctor_id", "created_at"),
        Index("ix_consultations_patient_created", "patient_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    doctor_id: Mapped[str] = mapped_column(String(36), ForeignKey("doctors.id", ondelete="CASCADE"), index=True, nullable=False)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), index=True, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="IN_PROGRESS", nullable=False)
    consent_status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    consent_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    audio_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    audio_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    doctor = relationship("Doctor", back_populates="consultations")
    patient = relationship("Patient", back_populates="consultations")
    transcript = relationship("Transcript", back_populates="consultation", uselist=False, cascade="all, delete-orphan")
    extraction = relationship("ClinicalExtraction", back_populates="consultation", uselist=False, cascade="all, delete-orphan")
    notes = relationship(
        "ClinicalNote",
        back_populates="consultation",
        cascade="all, delete-orphan",
        order_by="ClinicalNote.version.desc()",
    )
