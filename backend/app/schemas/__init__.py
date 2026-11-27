from app.schemas.auth import (
    DoctorResponse,
    DoctorUpdateRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.consultation import (
    ConsultationCreate,
    ConsultationDetailResponse,
    ConsultationSummary,
    ConsultationUpdate,
)
from app.schemas.dashboard import ActivityPoint, DashboardResponse, DashboardStats, RecentConsultationItem
from app.schemas.extraction import ClinicalExtractionPayload, ClinicalExtractionResponse
from app.schemas.note import (
    ClinicalNoteAmendRequest,
    ClinicalNoteApproveRequest,
    ClinicalNoteResponse,
    ClinicalNoteUpdateRequest,
    SoapNoteDraft,
)
from app.schemas.patient import PatientCreate, PatientResponse, PatientUpdate
from app.schemas.transcript import TranscriptResponse, TranscriptUpdateRequest

__all__ = [
    "RegisterRequest",
    "LoginRequest",
    "TokenResponse",
    "DoctorResponse",
    "DoctorUpdateRequest",
    "PatientCreate",
    "PatientUpdate",
    "PatientResponse",
    "ConsultationCreate",
    "ConsultationUpdate",
    "ConsultationSummary",
    "ConsultationDetailResponse",
    "TranscriptResponse",
    "TranscriptUpdateRequest",
    "ClinicalExtractionPayload",
    "ClinicalExtractionResponse",
    "SoapNoteDraft",
    "ClinicalNoteResponse",
    "ClinicalNoteUpdateRequest",
    "ClinicalNoteAmendRequest",
    "ClinicalNoteApproveRequest",
    "DashboardStats",
    "ActivityPoint",
    "RecentConsultationItem",
    "DashboardResponse",
]
