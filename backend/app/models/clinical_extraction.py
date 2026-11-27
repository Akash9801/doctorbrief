import uuid
from datetime import datetime, timezone
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ClinicalExtraction(Base):
    __tablename__ = "clinical_extractions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    consultation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("consultations.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    extracted_data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    missing_information: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    consultation = relationship("Consultation", back_populates="extraction")
