from datetime import datetime, timedelta, timezone
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.clinical_note import ClinicalNote
from app.models.consultation import Consultation
from app.models.patient import Patient
from app.schemas.dashboard import (
    ActivityPoint,
    DashboardResponse,
    DashboardStats,
    RecentConsultationItem,
)


def get_dashboard_data(db: Session, doctor_id: str) -> DashboardResponse:
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_patients = (
        db.query(func.count(Patient.id))
        .filter(Patient.doctor_id == doctor_id)
        .scalar()
        or 0
    )

    total_consultations = (
        db.query(func.count(Consultation.id))
        .filter(Consultation.doctor_id == doctor_id)
        .scalar()
        or 0
    )

    consultations_this_month = (
        db.query(func.count(Consultation.id))
        .filter(
            Consultation.doctor_id == doctor_id,
            Consultation.status == "COMPLETED",
            Consultation.started_at >= month_start,
        )
        .scalar()
        or 0
    )

    # Count consultations whose latest note version is DRAFT or UNDER_REVIEW
    consultations_with_notes = (
        db.query(Consultation)
        .options(joinedload(Consultation.notes))
        .filter(Consultation.doctor_id == doctor_id)
        .all()
    )
    notes_awaiting_approval = 0
    for c in consultations_with_notes:
        if c.notes:
            latest = max(c.notes, key=lambda n: n.version)
            if latest.status in {"DRAFT", "UNDER_REVIEW"}:
                notes_awaiting_approval += 1

    # Last 7 days activity (including today)
    seven_days_ago = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
    recent_7_consultations = (
        db.query(Consultation)
        .options(joinedload(Consultation.notes))
        .filter(
            Consultation.doctor_id == doctor_id,
            Consultation.started_at >= seven_days_ago,
        )
        .all()
    )

    day_buckets: dict[str, dict[str, int]] = {}
    ordered_days = []
    for offset in range(6, -1, -1):
        d = (now - timedelta(days=offset)).date()
        key = d.isoformat()
        ordered_days.append((key, d.strftime("%d %b")))
        day_buckets[key] = {"consultations": 0, "approved_notes": 0}

    for c in recent_7_consultations:
        c_date = c.started_at.date().isoformat()
        if c_date in day_buckets:
            day_buckets[c_date]["consultations"] += 1
            if any(n.status == "APPROVED" for n in c.notes):
                day_buckets[c_date]["approved_notes"] += 1

    activity_points = [
        ActivityPoint(
            date=key,
            label=label,
            consultations=day_buckets[key]["consultations"],
            approved_notes=day_buckets[key]["approved_notes"],
        )
        for key, label in ordered_days
    ]

    recent_rows = (
        db.query(Consultation)
        .options(
            joinedload(Consultation.patient),
            joinedload(Consultation.notes),
        )
        .filter(Consultation.doctor_id == doctor_id)
        .order_by(Consultation.started_at.desc())
        .limit(8)
        .all()
    )

    recent_items = []
    for c in recent_rows:
        notes_sorted = sorted(c.notes, key=lambda n: n.version, reverse=True)
        note_status = notes_sorted[0].status if notes_sorted else "NONE"
        recent_items.append(
            RecentConsultationItem(
                id=c.id,
                patient_id=c.patient_id,
                patient_name=c.patient.full_name,
                patient_code=c.patient.patient_code,
                consultation_date=c.started_at,
                consultation_status=c.status,
                note_status=note_status,
            )
        )

    return DashboardResponse(
        stats=DashboardStats(
            total_patients=total_patients,
            total_consultations=total_consultations,
            consultations_this_month=consultations_this_month,
            notes_awaiting_approval=notes_awaiting_approval,
        ),
        activity_last_7_days=activity_points,
        recent_consultations=recent_items,
    )
