import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ClinicalNote(Base):
    __tablename__ = "clinical_notes"
    __table_args__ = (
        Index("ix_clinical_notes_consultation_version", "consultation_id", "version"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    consultation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("consultations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    subjective: Mapped[str] = mapped_column(Text, default="", nullable=False)
    objective: Mapped[str] = mapped_column(Text, default="", nullable=False)
    assessment: Mapped[str] = mapped_column(Text, default="", nullable=False)
    plan: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="DRAFT", index=True, nullable=False)
    amendment_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_note_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("clinical_notes.id", ondelete="SET NULL"), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("doctors.id", ondelete="SET NULL"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    consultation = relationship("Consultation", back_populates="notes")
    approver = relationship("Doctor", foreign_keys=[approved_by])
