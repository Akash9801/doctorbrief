from datetime import datetime
from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_patients: int
    total_consultations: int
    consultations_this_month: int
    notes_awaiting_approval: int


class ActivityPoint(BaseModel):
    date: str
    label: str
    consultations: int
    approved_notes: int


class RecentConsultationItem(BaseModel):
    id: str
    patient_id: str
    patient_name: str
    patient_code: str
    consultation_date: datetime
    consultation_status: str
    note_status: str


class DashboardResponse(BaseModel):
    stats: DashboardStats
    activity_last_7_days: list[ActivityPoint]
    recent_consultations: list[RecentConsultationItem]
